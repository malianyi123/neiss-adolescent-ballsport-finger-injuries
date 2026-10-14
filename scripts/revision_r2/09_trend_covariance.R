#!/usr/bin/env Rscript
# ---------------------------------------------------------------------------
# Second revision, R1.1 + R2.5
#   (1) build the survey design on the FULL pooled NEISS file, then subset()
#   (2) estimate the full variance-covariance matrix of the annual totals
#   (3) refit the trend under four treatments of the covariance
# Writes outputs/reports/trend_covariance.csv and annual_covariance.csv
# ---------------------------------------------------------------------------
suppressPackageStartupMessages(library(survey))
options(survey.lonely.psu = "adjust")

args <- commandArgs(trailingOnly = TRUE)
root <- if (length(args) >= 1) normalizePath(args[1]) else getwd()
Z <- qnorm(0.975)

## ---- 1. full file (all years), with a cohort flag -------------------------
years <- 2015:2025
read_year <- function(y) {
  f <- file.path(root, "data", "raw", "neiss", sprintf("neiss%d.tsv", y))
  d <- read.delim(f, colClasses = "character", quote = "\"", na.strings = "",
                  fileEncoding = "latin1")
  data.frame(case_id = d$CPSC_Case_Number, year = y,
             stratum = d$Stratum, psu = as.integer(d$PSU),
             weight = as.numeric(d$Weight), stringsAsFactors = FALSE)
}
full <- do.call(rbind, lapply(years, read_year))
full <- full[!is.na(full$weight) & !is.na(full$psu) & !is.na(full$stratum), ]

cohort <- read.csv(file.path(root, "data", "processed", "cohort_main.csv"))
full$in_cohort <- full$case_id %in% as.character(cohort$case_id)
stopifnot(sum(full$in_cohort) == nrow(cohort))

## ---- 2. DESIGN-THEN-SUBSET ------------------------------------------------
des_full <- svydesign(ids = ~psu, strata = ~stratum, weights = ~weight,
                      nest = TRUE, data = full)
des <- subset(des_full, in_cohort)

# diagnostic reported in the manuscript: do any sampling units drop out?
cl_full <- unique(full[, c("stratum", "psu")])
cl_coh  <- unique(full[full$in_cohort, c("stratum", "psu")])
cat(sprintf("clusters in pooled file: %d ; contributing >=1 cohort record: %d\n",
            nrow(cl_full), nrow(cl_coh)))

## ---- 3. annual totals WITH the full covariance matrix ---------------------
des <- update(des, one = 1)
ann <- svyby(~one, ~year, des, svytotal, covmat = TRUE)
est <- as.numeric(coef(ann))
V   <- vcov(ann)                       # <- the object R1.1 asked for
se  <- sqrt(diag(V))
R   <- V / outer(se, se)
write.csv(R, file.path(root, "outputs", "reports", "annual_correlation.csv"))
cat(sprintf("mean off-diagonal correlation: %.3f (median %.3f)\n",
            mean(R[upper.tri(R)]), median(R[upper.tri(R)])))

## ---- 4. four treatments of the covariance ---------------------------------
fit <- function(idx, log_scale, mode) {
  x  <- years[idx]; y <- est[idx]; Vs <- V[idx, idx, drop = FALSE]
  if (log_scale) { Vs <- Vs / outer(y, y); y <- log(y) }
  s0 <- sqrt(diag(Vs))
  X  <- cbind(1, x - mean(x))
  if (mode == "fixed_w") {                      # (B) PRIMARY
    W  <- diag(1 / s0^2)                        # prespecified weights, held fixed
    A  <- solve(t(X) %*% W %*% X)
    L  <- (A %*% t(X) %*% W)[2, ]               # slope = L . y
    b  <- as.numeric(L %*% y)
    s  <- sqrt(as.numeric(t(L) %*% Vs %*% L))   # design-based variance a'Va
  } else {
    Vu <- switch(mode,
      indep = diag(s0^2),                                        # (A)
      gls   = Vs,                                                # (C)
      exch  = { Rr <- Vs / outer(s0, s0); k <- length(idx)
                rho <- (sum(Rr) - k) / (k * (k - 1))
                outer(s0, s0) * ((1 - rho) * diag(k) + rho) })    # (D)
    Vi <- solve(Vu); A <- solve(t(X) %*% Vi %*% X)
    bb <- A %*% (t(X) %*% Vi %*% y); b <- bb[2]; s <- sqrt(A[2, 2])
  }
  p <- 2 * pnorm(-abs(b / s))
  if (log_scale) c(est = (exp(b) - 1) * 100, lo = (exp(b - Z * s) - 1) * 100,
                   hi = (exp(b + Z * s) - 1) * 100, p = p)
  else           c(est = b, lo = b - Z * s, hi = b + Z * s, p = p)
}

periods <- list("Full study period"        = which(years %in% 2015:2025),
                "Pre-pandemic"             = which(years %in% 2015:2019),
                "Post-pandemic"            = which(years %in% 2022:2025),
                "Excluding pandemic years" = which(!years %in% c(2020, 2021)))
out <- do.call(rbind, lapply(names(periods), function(nm)
  do.call(rbind, lapply(c(FALSE, TRUE), function(lg)
    do.call(rbind, lapply(c("indep", "fixed_w", "gls", "exch"), function(md) {
      r <- fit(periods[[nm]], lg, md)
      data.frame(period = nm, scale = if (lg) "pct_per_year" else "visits_per_year",
                 method = md, estimate = r[["est"]], ci_lo = r[["lo"]],
                 ci_hi = r[["hi"]], p = r[["p"]], row.names = NULL)
    }))))))
write.csv(out, file.path(root, "outputs", "reports", "trend_covariance.csv"),
          row.names = FALSE)
print(out, digits = 4)
