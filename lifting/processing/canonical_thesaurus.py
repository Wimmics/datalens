import re
from .parser_tools import dedupe, normalize_string

MODALITY_CANONICAL = {
    '3d': '3D',
    'audio': 'Audio',
    'document': 'Document',
    'geospatial': 'Geospatial',
    'image': 'Image',
    'tabular': 'Tabular',
    'text': 'Text',
    'timeseries': 'TimeSeries',
    'time_series': 'TimeSeries',
    'time-series': 'TimeSeries',
    'video': 'Video',
}

TRANSFORMATION_CANONICAL = {
    'finetune': 'Finetune',
    'quantize': 'Quantize',
    'merge': 'Merge',
    'adapt': 'Adapt',
}

FORMAT_CANONICAL = {
    'webdataset': 'WebDataset',
    'imagefolder': 'ImageFolder',
    'audiofolder': 'AudioFolder',
    'agent-traces': 'AgentTraces',
    'arrow': 'Arrow',
    'csv': 'CSV',
    'json': 'JSON',
    'parquet': 'Parquet',
    'optimized-parquet': 'OptimizedParquet',
    'text': 'Text',
}

SIZE_CATEGORY_CANONICAL = {
    'n<1k': '1',
    '<1k': '1',
    'lt-1k': '1',
    'size-lt-1k': '1',
    '1k<n<10k': '1k',
    'size-1k-to-10k': '1k',
    '10k<n<100k': '10k',
    'size-10k-to-100k': '10k',
    '100k<n<1m': '100k',
    'size-100k-to-1m': '100k',
    '1m<n<10m': '1m',
    'size-1m-to-10m': '1m',
    '10m<n<100m': '10m',
    'size-10m-to-100m': '10m',
    '100m<n<1b': '100m',
    'size-100m-to-1b': '100m',
    '1b<n<10b': '1b',
    'size-1b-to-10b': '1b',
    '10b<n<100b': '10b',
    'size-10b-to-100b': '10b',
    '100b<n<1t': '100b',
    'size-100b-to-1t': '100b',
    'n>1t': '1t',
    '>1t': '1t',
    'gt-1t': '1t',
    'size-gt-1t': '1t',
}

DATASET_LIBRARY_CANONICAL = {
    'datadesigner': 'DataDesigner',
    'lance': 'Lance',
    'datasets': 'Datasets',
    'webdataset': 'WebDataset',
    'polars': 'Polars',
    'dask': 'Dask',
    'pandas': 'Pandas',
    'fiftyone': 'FiftyOne',
    'distilabel': 'Distilabel',
    'mlcroissant': 'MLCroissant',
    'argilla': 'Argilla',
}

MODEL_LIBRARY_CANONICAL = {
    'pytorch': 'Pytorch',
    'sklearn': 'Sklearn',
    'transformers.js': 'TransformersJS',
    'transformers': 'Transformers',
    'allennlp': 'Allennlp',
    'stanza': 'Stanza',
    'PaddleOCR': 'PaddleOCR',
    'adapter-transformers': 'AdapterTransformers',
    'rust': 'Rust',
    'keras-hub': 'KerasHub',
    'sentence-transformers': 'SentenceTransformers',
    'speechbrain': 'Speechbrain',
    'tflite': 'LiteRT',
    'espnet': 'Espnet',
    'pyannote-audio': 'PyannoteAudio',
    'open-clip': 'OpenClip',
    'peft': 'Peft',
    'fasttext': 'Fasttext',
    'tensorboard': 'Tensorboard',
    'keras': 'Keras',
    'stable-baselines3': 'StableBaselines3',
    'nemo': 'Nemo',
    'asteroid': 'Asteroid',
    'optimum_graphcore': 'OptimumGraphcore',
    'tf-keras': 'TFKeras',
    'span-marker': 'SpanMarker',
    'paddlenlp': 'PaddleNLP',
    'joblib': 'Joblib',
    'optimum_habana': 'OptimumHabana',
    'univa': 'Univa',
    'dduf': 'DDUF',
    'openvino': 'OpenVINO',
    'gguf': 'GGUF',
    'flair': 'Flair',
    'coreml': 'CoreML',
    'setfit': 'SetFit',
    'onnx': 'ONNX',
    'jax': 'Jax',
    'spacy': 'Spacy',
    'diffusers': 'Diffusers',
    'llamafile': 'LlamaFile',
    'sample-factory': 'SampleFactory',
    'fairseq': 'Fairseq',
    'timm': 'Timm',
    'paddlepaddle': 'PaddlePaddle',
    'ml-agents': 'MLAgents',
    'fastai': 'FastAI',
    'executorch': 'ExecuTorch',
    'tf': 'TF',
    'mlx': 'MLX',
    'unity-sentis': 'UnitySentis',
    'safetensors': 'Safetensors',
    'bertopic': 'BERTopic',
}

TASK_CANONICAL = {
    'document-question-answering': 'DocumentQuestionAnswering',
    'audio-classification': 'AudioClassification',
    'image-to-image': 'ImageToImage',
    'tabular-regression': 'TabularRegression',
    'image-segmentation': 'ImageSegmentation',
    'unconditional-image-generation': 'UnconditionalImageGeneration',
    'image-to-text': 'ImageToText',
    'any-to-any': 'AnyToAny',
    'zero-shot-classification': 'ZeroShotClassification',
    'time-series-forecasting': 'TimeSeriesForecasting',
    'zero-shot-object-detection': 'ZeroShotObjectDetection',
    'robotics': 'Robotics',
    'reinforcement-learning': 'ReinforcementLearning',
    'mask-generation': 'MaskGeneration',
    'feature-extraction': 'FeatureExtraction',
    'text-to-audio': 'TextToAudio',
    'audio-to-audio': 'AudioToAudio',
    'image-to-video': 'ImageToVideo',
    'video-classification': 'VideoClassification',
    'tabular-to-text': 'TabularToText',
    'fill-mask': 'FillMask',
    'object-detection': 'ObjectDetection',
    'zero-shot-image-classification': 'ZeroShotImageClassification',
    'token-classification': 'TokenClassification',
    'image-feature-extraction': 'ImageFeatureExtraction',
    'text-to-video': 'TextToVideo',
    'image-classification': 'ImageClassification',
    'text-generation': 'TextGeneration',
    'tabular-classification': 'TabularClassification',
    'multiple-choice': 'MultipleChoice',
    'image-text-to-text': 'ImageTextToText',
    'visual-question-answering': 'VisualQuestionAnswering',
    'summarization': 'Summarization',
    'image-text-to-image': 'ImageTextToImage',
    'sentence-similarity': 'SentenceSimilarity',
    'text-to-3d': 'TextTo3D',
    'video-text-to-text': 'VideoTextToText',
    'image-to-3d': 'ImageTo3D',
    'visual-document-retrieval': 'VisualDocumentRetrieval',
    'automatic-speech-recognition': 'AutomaticSpeechRecognition',
    'audio-text-to-text': 'AudioTextToText',
    'text-retrieval': 'TextRetrieval',
    'depth-estimation': 'DepthEstimation',
    'table-to-text': 'TableToText',
    'image-text-to-video': 'ImageTextToVideo',
    'table-question-answering': 'TableQuestionAnswering',
    'question-answering': 'QuestionAnswering',
    'graph-ml': 'GraphML',
    'translation': 'Translation',
    'keypoint-detection': 'KeypointDetection',
    'voice-activity-detection': 'VoiceActivityDetection',
    'text-classification': 'TextClassification',
    'text-to-speech': 'TextToSpeech',
    'text-to-image': 'TextToImage',
    'video-to-video': 'VideoToVideo',
    'text-ranking': 'TextRanking',
}

SUBTASK_CANONICAL = {
    'named-entity-recognition': 'NamedEntityRecognition',
    'pose-estimation': 'PoseEstimation',
    'document-question-answering': 'DocumentQuestionAnswering',
    'open-domain-abstractive-qa': 'OpenDomainAbstractiveQA',
    'entity-linking-retrieval': 'EntityLinkingRetrieval',
    'multi-class-image-classification': 'MultiClassImageClassification',
    'explanation-generation': 'ExplanationGeneration',
    'multi-input-text-classification': 'MultiInputTextClassification',
    'keyword-spotting': 'KeywordSpotting',
    'dialogue-generation': 'DialogueGeneration',
    'tabular-multi-label-classification': 'TabularMultiLabelClassification',
    'part-of-speech': 'PartOfSpeech',
    'language-modeling': 'LanguageModeling',
    'multi-label-classification': 'MultiLabelClassification',
    'super-resolution': 'SuperResolution',
    'univariate-time-series-forecasting': 'UnivariateTimeSeriesForecasting',
    'entity-linking-classification': 'EntityLinkingClassification',
    'text-simplification': 'TextSimplification',
    'natural-language-inference': 'NaturalLanguageInference',
    'image-inpainting': 'ImageInpainting',
    'conversational': 'Conversational',
    'text-scoring': 'TextScoring',
    'hate-speech-detection': 'HateSpeechDetection',
    'dialogue-modeling': 'DialogueModeling',
    'speaker-identification': 'SpeakerIdentification',
    'closed-book-qa': 'ClosedBookQA',
    'news-articles-summarization': 'NewsArticlesSummarization',
    'coreference-resolution': 'CoreferenceResolution',
    'news-articles-headline-generation': 'NewsArticlesHeadlineGeneration',
    'document-retrieval': 'DocumentRetrieval',
    'semantic-similarity-scoring': 'SemanticSimilarityScoring',
    'parsing': 'Parsing',
    'lemmatization': 'Lemmatization',
    'multiple-choice-qa': 'MultipleChoiceQA',
    'multi-label-image-classification': 'MultiLabelImageClassification',
    'sentiment-classification': 'SentimentClassification',
    'utterance-retrieval': 'UtteranceRetrieval',
    'panoptic-segmentation': 'PanopticSegmentation',
    'slot-filling': 'SlotFilling',
    'image-captioning': 'ImageCaptioning',
    'audio-language-identification': 'AudioLanguageIdentification',
    'visual-question-answering': 'VisualQuestionAnswering',
    'topic-classification': 'TopicClassification',
    'multivariate-time-series-forecasting': 'MultivariateTimeSeriesForecasting',
    'semantic-similarity-classification': 'SemanticSimilarityClassification',
    'audio-intent-classification': 'AudioIntentClassification',
    'rdf-to-text': 'RDFToText',
    'fact-checking': 'FactChecking',
    'sentiment-scoring': 'SentimentScoring',
    'semantic-segmentation': 'SemanticSegmentation',
    'extractive-qa': 'ExtractiveQA',
    'grasping': 'Grasping',
    'vehicle-detection': 'VehicleDetection',
    'language-identification': 'LanguageIdentification',
    'text2textgeneration': 'Text2TextGeneration',
    'open-domain-qa': 'OpenDomainQA',
    'fact-checking-retrieval': 'FactCheckingRetrieval',
    'image-colorization': 'ImageColorization',
    'open-book-qa': 'OpenBookQA',
    'task-planning': 'TaskPlanning',
    'masked-language-modeling': 'MaskedLanguageModeling',
    'abstractive-qa': 'AbstractiveQA',
    'instance-segmentation': 'InstanceSegmentation',
    'intent-classification': 'IntentClassification',
    'sentiment-analysis': 'SentimentAnalysis',
    'word-sense-disambiguation': 'WordSenseDisambiguation',
    'multi-class-classification': 'MultiClassClassification',
    'acceptability-classification': 'AcceptabilityClassification',
    'tabular-single-column-regression': 'TabularSingleColumnRegression',
    'closed-domain-qa': 'ClosedDomainQA',
    'face-detection': 'FaceDetection',
    'multiple-choice-coreference-resolution': 'MultipleChoiceCoreferenceResolution',
    'audio-emotion-recognition': 'AudioEmotionRecognition',
    'tabular-multi-class-classification': 'TabularMultiClassClassification',
}

CANONICALS = {
    "modality": MODALITY_CANONICAL,
    "transformation": TRANSFORMATION_CANONICAL,
    "format": FORMAT_CANONICAL,
    "size_category": SIZE_CATEGORY_CANONICAL,
    "dataset_library": DATASET_LIBRARY_CANONICAL,
    "model_library": MODEL_LIBRARY_CANONICAL,
    "task": TASK_CANONICAL,
    "subtask": SUBTASK_CANONICAL,
}


def _canonical_lookup(value: str, canonical: str) -> str | None:
    mapping = CANONICALS.get(canonical, {})

    token = normalize_string(value)
    if not token:
        return None

    compact = re.sub(r"[-_\s]", "", token.lower())
    direct = mapping.get(token.lower()) or mapping.get(token) or mapping.get(compact)
    if direct:
        return direct

    camel_hyphen = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "-", token)
    camel_hyphen = re.sub(r"([0-9])-(?=[A-Za-z])", r"\1", camel_hyphen)
    camel_key = camel_hyphen.replace("_", "-").lower()
    return mapping.get(camel_key) or mapping.get(re.sub(r"[-_\s]", "", camel_key))

def canonicalize(values: list[str], canonical: str | None = None) -> list[str]:
    canonical = canonical or "task"
    output: list[str] = []
    for value in values:
        canonical_localname = _canonical_lookup(value, canonical)
        if not canonical_localname:
            continue
        output.append(canonical_localname)

    return dedupe(output)

def get_tag_alone(tags: list[str], canonical: str) -> list[str]:
    values: list[str] = []
    mapping = CANONICALS.get(canonical, {})
    if not mapping:
        return []

    known_keys = set(mapping.keys())
    compact_keys = {re.sub(r"[-_\s]", "", key.lower()) for key in known_keys}

    for tag in tags:
        token = normalize_string(tag)
        if not token or ":" in token:
            continue

        normalized = token.lower()
        compact = re.sub(r"[-_\s]", "", normalized)

        if normalized in known_keys or compact in compact_keys:
            values.append(token)
            tags.remove(tag)
            continue

        if _canonical_lookup(token, canonical):
            values.append(token)
            tags.remove(tag)

    return dedupe(values)