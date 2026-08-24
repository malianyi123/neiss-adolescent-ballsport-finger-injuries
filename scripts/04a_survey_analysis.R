#!/usr/bin/env Rscript

options(stringsAsFactors = FALSE)
options(survey.lonely.psu = "adjust")

trailing <- commandArgs(trailingOnly = TRUE)
if (length(trailing) >= 1) {
  root <- normalizePath(trailing[1], mustWork = TRUE)
} else {
  cmd_args <- commandArgs(trailingOnly = FALSE)
  file_arg <- sub("^--file=", "", cmd_args[grep("^--file=", cmd_args)][1])
  root <- normalizePath(file.path(dirname(file_arg), ".."), mustWork = TRUE)
}
cohort_path <- file.path(root, "data", "processed", "cohort_main.csv")
report_dir <- file.path(root, "outputs", "reports")
status_path <- file.path(report_dir, "r_survey_status.txt")

write_status <- function(text) {
  writeLines(text, status_path)
}

if (!requireNamespace("survey", quietly = TRUE)) {
  write_status("R survey package is not installed; Python fallback outputs were retained.")
  quit(status = 2)
}

suppressPackageStartupMessages(library(survey))

df <- read.csv(cohort_path, check.names = FALSE)
df <- df[!is.na(df$weight) & !is.na(df$stratum) & !is.na(df$psu), ]
df$one <- 1
df$year <- as.integer(df$year)
df$sport_group <- as.factor(df$sport_group)
df$age_group <- factor(df$age_group, levels = c("10-12", "13-15", "16-18"))
df$sex_clean <- factor(df$sex_clean, levels = c("male", "female", "unknown/other"))
df$diagnosis_group <- factor(df$diagnosis_group, levels = c("fracture", "dislocation"))

des <- svydesign(ids = ~psu, strata = ~stratum, weights = ~weight, nest = TRUE, data = df)

flag_instability <- function(n, estimate, cv) {
  flags <- c()
  if (is.na(estimate) || estimate < 1200) flags <- c(flags, "estimate<1200")
  if (is.na(n) || n < 20) flags <- c(flags, "n<20")
  if (!is.na(cv) && cv > 0.33) flags <- c(flags, "cv>33%")
  paste(flags, collapse = "; ")
}

annual <- svyby(~one, ~year, des, svytotal, vartype = c("se", "cv"), keep.names = FALSE)
annual_n <- as.data.frame(table(df$year))
names(annual_n) <- c("year", "unweighted_n")
annual$year <- as.integer(as.character(annual$year))
annual <- merge(annual, annual_n, by = "year", all.x = TRUE)
annual_out <- data.frame(
  year = annual$year,
  unweighted_n = annual$unweighted_n,
  weighted_estimate = as.numeric(annual$one),
  se = as.numeric(annual$se),
  cv = as.numeric(annual$cv),
  instability_flag = mapply(flag_instability, annual$unweighted_n, annual$one, annual$cv)
)
write.csv(annual_out, file.path(report_dir, "annual_estimates.csv"), row.names = FALSE)
write.csv(annual_out, file.path(report_dir, "r_survey_annual_estimates.csv"), row.names = FALSE)

sport <- svyby(~one, ~sport_group, des, svytotal, vartype = c("se", "cv"), keep.names = FALSE)
sport_n <- as.data.frame(table(df$sport_group))
names(sport_n) <- c("sport_group", "unweighted_n")
sport$sport_group <- as.character(sport$sport_group)
sport <- merge(sport, sport_n, by = "sport_group", all.x = TRUE)
sport_out <- data.frame(
  sport_group = sport$sport_group,
  unweighted_n = sport$unweighted_n,
  weighted_estimate = as.numeric(sport$one),
  se = as.numeric(sport$se),
  cv = as.numeric(sport$cv),
  instability_flag = mapply(flag_instability, sport$unweighted_n, sport$one, sport$cv)
)
write.csv(sport_out, file.path(report_dir, "r_survey_sport_totals.csv"), row.names = FALSE)

model_df <- df[df$sex_clean %in% c("male", "female"), ]
sport_totals <- aggregate(weight ~ sport_group, data = model_df, sum)
sport_totals <- sport_totals[order(-sport_totals$weight), ]
ref_sport <- as.character(sport_totals$sport_group[1])
model_df$sport_group <- relevel(factor(model_df$sport_group), ref = ref_sport)
model_df$sex_clean <- relevel(factor(as.character(model_df$sex_clean)), ref = "male")
model_df$age_group <- relevel(factor(as.character(model_df$age_group)), ref = "10-12")
model_df$dislocation <- as.integer(model_df$diagnosis_group == "dislocation")
model_df$year_centered <- model_df$year - median(model_df$year, na.rm = TRUE)
model_des <- svydesign(ids = ~psu, strata = ~stratum, weights = ~weight, nest = TRUE, data = model_df)
fit <- svyglm(dislocation ~ sport_group + age_group + sex_clean + year_centered,
              design = model_des, family = quasibinomial())
co <- coef(fit)
ci <- suppressMessages(confint(fit))
summ <- summary(fit)$coefficients
terms <- names(co)
keep <- terms != "(Intercept)"

clean_term <- function(term) {
  if (startsWith(term, "sport_group")) {
    lev <- sub("^sport_group", "", term)
    return(paste0("sport group: ", lev, " vs ", ref_sport))
  }
  if (startsWith(term, "age_group")) {
    lev <- sub("^age_group", "", term)
    return(paste0("age group: ", lev, " vs 10-12"))
  }
  if (startsWith(term, "sex_clean")) {
    lev <- sub("^sex_clean", "", term)
    return(paste0("sex: ", lev, " vs male"))
  }
  if (term == "year_centered") return("treatment year, per year")
  term
}

model_out <- data.frame(
  term = vapply(terms[keep], clean_term, character(1)),
  adjusted_or = exp(co[keep]),
  ci_low = exp(ci[keep, 1]),
  ci_high = exp(ci[keep, 2]),
  p_value = summ[keep, 4],
  reference = paste0("sport reference: ", ref_sport, "; outcome reference: fracture"),
  se_note = "R survey::svyglm with NEISS strata, PSU, and weights",
  row.names = NULL
)
write.csv(model_out, file.path(report_dir, "model_dislocation_vs_fracture.csv"), row.names = FALSE)
write.csv(model_out, file.path(report_dir, "r_survey_model_dislocation_vs_fracture.csv"), row.names = FALSE)
capture.output(summary(fit), file = file.path(report_dir, "r_survey_model_dislocation_summary.txt"))
write_status("R survey analysis completed successfully using survey::svydesign and survey::svyglm.")
