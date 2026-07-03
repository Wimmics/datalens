import { promises as fs } from "node:fs";
import path from "node:path";
import { exit } from "node:process";
import { fileURLToPath } from "node:url";

import { parseArgs } from "node:util";

const { values } = parseArgs({
  options: {
    inputFolder: {
      type: "string",
      short: "i",
    },
    outputFolder: {
      type: "string",
      short: "o",
    },
	ignore: { // list of files to ignore in the given input folder
      type: "string",
      multiple: true,
    }
  },
});

console.log(values)

const ENDPOINT_URL = "https://[anonymous]/repositories/datalens";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const SPARQL_DIR = path.resolve(__dirname, values.inputFolder);
const OUTPUT_DIR = path.resolve(__dirname, values.outputFolder)

await fs.mkdir(OUTPUT_DIR, { recursive: true });

function toCacheFilename(queryFilename) {
	const base = path.basename(queryFilename, ".rq");
	return `${base}.json`;
}

async function readQueryFiles() {
	const entries = await fs.readdir(SPARQL_DIR, { withFileTypes: true });
	console.log(entries)
	return entries
		.filter((entry) => entry.isFile() && 
						entry.name.endsWith(".rq") && 
						!values.ignore?.includes(entry.name))
		.map((entry) => entry.name)
		.sort((a, b) => a.localeCompare(b));
}

async function runSparqlQuery(queryText) {
	const response = await fetch(ENDPOINT_URL, {
		method: "POST",
		headers: {
			"Content-Type": "application/sparql-query",
			Accept: "application/sparql-results+json, application/json",
		},
		body: queryText,
	});

	if (!response.ok) {
		const body = await response.text().catch(() => "");
		throw new Error(
			`Endpoint returned ${response.status} ${response.statusText}${
				body ? `\n${body}` : ""
			}`
		);
	}

	return response.json();
}

async function saveResultFile(queryFilename, data) {
	const outputPath = path.join(OUTPUT_DIR, toCacheFilename(queryFilename));
	await fs.writeFile(outputPath, JSON.stringify(data, null, 2), "utf8");
	return outputPath;
}

async function main() {
	console.log(`SPARQL source folder: ${SPARQL_DIR}`);
	console.log(`Cache destination folder: ${OUTPUT_DIR}`);
	console.log(`Endpoint: ${ENDPOINT_URL}`);

	const queryFiles = await readQueryFiles();

	if (queryFiles.length === 0) {
		console.log("No .rq files found. Nothing to fetch.");
		return;
	}

	console.log(`Found ${queryFiles.length} query file(s).`);

	for (const filename of queryFiles) {
		const queryPath = path.join(SPARQL_DIR, filename);
		process.stdout.write(`Running ${filename} ... `);

		try {
			const queryText = await fs.readFile(queryPath, "utf8");
			const result = await runSparqlQuery(queryText);
			const outputPath = await saveResultFile(filename, result);
			console.log(`OK -> ${path.basename(outputPath)}`);
		} catch (error) {
			const message = error instanceof Error ? error.message : String(error)
			console.log("FAILED. Reason: ", message)
		}
	}

	console.log("\nDone!");
}

main().catch((error) => {
	console.error("Unexpected error while fetching SPARQL data.");
	console.error(error instanceof Error ? error.stack : error);
	process.exitCode = 1;
});
