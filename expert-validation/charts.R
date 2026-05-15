library(tidyverse)
library(scales)
library(ggpubr)
library(cowplot)

data_df <- read.csv("data/results.csv") 
data_df <- na.omit(data_df)

# Task normalization for visualization
data_df$task <- gsub(
  "Subtask : (.*) - Task\\(s\\) : (.*)",
  "\\1 → \\2",
  data_df$task
)

# -----------------------------------
# Agreement level normalization for analysis and visualization
data_df$reported.agreement <- factor(
  data_df$reported.agreement,
  levels = c(
    "Not at all relevant",
    "Slightly relevant",
    "Somewhat relevant",
    "Very relevant",
    "Extremely relevant"
  )
)

agreement_scores <- c(
  "Not at all relevant" = 1,
  "Slightly relevant" = 2,
  "Somewhat relevant" = 3,
  "Very relevant" = 4,
  "Extremely relevant" = 5
)

data_df <- data_df %>%
  mutate(
    agreement_score = agreement_scores[reported.agreement]
  )

task_order <- data_df %>%
  group_by(task) %>%
  summarise(mean_agreement = mean(agreement_score, na.rm = TRUE)) %>%
  arrange(mean_agreement)

data_df$task <- factor(
  data_df$task,
  levels = task_order$task
)

#----------------------------------
# Agreement level per task-subtask association

# Charts common styling
common_theme <- theme(
  plot.margin = margin(
    t = 10,
    r = 10,
    b = 10,
    l = 40
  ),
  panel.grid = element_blank(),
  axis.text.y = element_text(size = 10.5, margin = margin(r = -2))
)

# Group 1 responses
p1 <- ggplot(subset(data_df, questionnaire_id == 1), aes(x = task, fill = reported.agreement)) +
  geom_bar() +
  scale_fill_brewer(palette = "Blues") +
  coord_flip() +
  theme_minimal() + common_theme + theme(legend.position = "bottom") +
  labs(
    x = "Subtask → Task Association (Group 1)",
    y = "Number of responses per agreement level",
    fill = "Agreement"
  )

# Group 2 responses
p2 <- ggplot(subset(data_df, questionnaire_id == 2), aes(x = task, fill = reported.agreement)) +
  geom_bar() +
  scale_fill_brewer(palette = "Blues") +
  coord_flip() +
  theme_minimal() + common_theme + theme(legend.position = "none") +
  labs(
    x = "Subtask → Task Association (Group 2)",
    y = "Number of responses per agreement level",
    fill = "Agreement"
  )

aligned <- align_plots(
  p1,
  p2,
  align = "v",
  axis = "l"
)

ggarrange(
  aligned[[1]],
  aligned[[2]],
  ncol = 2
)

ggsave("charts/agreement_task.png", device = "png", width = 20, height = 10)


#-----------------------
# Frequency of agreement level cooccurrence

# Charts common styling
freq_common_theme <- theme(axis.text.x = element_text(size = 12), 
                           axis.text.y = element_text(size = 12),
                           axis.title.x = element_blank(),
                           axis.title.y = element_text(size = 14),
                           legend.title = element_text(size = 14), 
                           legend.text = element_text(size=12)) 

freq_y_axis =  scale_y_continuous(
  limits = c(0, 22),
  breaks = seq(0, 22, 2),
  expand = c(0, 0)
)

# Group 1
count_group1 <- subset(data_df, questionnaire_id == 1) %>% group_by(task, reported.agreement) %>% summarise(count = n())
agreement_group1 <- count_group1 %>% 
  group_by(reported.agreement, count) %>% 
  summarise(freq=n()) %>%
  ungroup() %>%
  complete(
    reported.agreement,
    count,
    fill = list(freq = 0)
  )

freq1 <- ggplot(agreement_group1, aes(x = reported.agreement, y = freq,  fill = as.factor(count))) +
  geom_col(position = "dodge") +
  theme_bw() + 
  freq_common_theme +
  labs(y = "Frequency of response", 
       fill = "Number of Respondents") +
  freq_y_axis

# Group 2
count_group2 <- subset(data_df, questionnaire_id == 2) %>% group_by(task, reported.agreement) %>% summarise(count = n())
agreement_group2 <- count_group2 %>% 
  group_by(reported.agreement, count) %>% 
  summarise(freq=n()) %>%
  ungroup() %>%
  complete(
    reported.agreement,
    count,
    fill = list(freq = 0)
  )


freq2 <- ggplot(agreement_group2, aes(x = reported.agreement, y = freq,  fill = as.factor(count))) +
  geom_col(position = "dodge") +
  theme_bw() + freq_common_theme +
  labs(y = "Frequency of response", 
       fill = "Number of Respondents") +
  freq_y_axis 


ggarrange(
  freq1,
  freq2,
  ncol = 2,
  common.legend = TRUE,
  legend = "top"
)

ggsave("charts/agreement_freq.png", device = "png", width = 15, height = 5)
