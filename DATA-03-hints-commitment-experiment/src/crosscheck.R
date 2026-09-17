# ============================================================================
# Independent R cross-check of the Phase 4b weighting harness (src/weighting.py)
# ----------------------------------------------------------------------------
# Confirms the corrected Python jackknife against survey::svrepdesign using
# NCI's OWN replication parameters, derived here from NCI's documentation rather
# than copied from the Python constants.
#
#   type    = "JKn"          NCI "HINTS 7 Survey Overview Data Analysis
#   scale   = 0.98            Recommendations", R section (Analyzing Data Using R
#   rscales = rep(1, 50)      -> R Replicate Weights Variance Estimation Method):
#   mse     = TRUE              as_survey_rep(..., type = "JKn", scale = 0.98,
#                                              rscales = rep(1, times = 50))
#
# The survey-package replication variance is
#     Var = scale * sum_i [ rscales_i * (theta_i - theta_0)^2 ]
#         = 0.98  * sum_{i=1}^{50} (theta_i - theta_0)^2          (mse = TRUE)
# i.e. NO division by the replicate count. This is exactly what the corrected
# jackknife_se() computes. The Phase 4 error was an extra "/ 50".
#
# RUN (Windows, PowerShell -- R segfaults under Git Bash on this machine):
#   & "C:\Program Files\R\R-4.6.1\bin\Rscript.exe" src\crosscheck.R
#
# Needs: the `survey` package, hints7_public.rda, and
#        data/processed/analysis_frame_r_export.csv (written by
#        src/validate_harness.py). No `arrow` required -- Windows was blocking
#        the arrow native library, so the frame's rates come in via CSV and are
#        joined to the .rda's weights by row order (respondent_idx 0..7277 maps
#        to .rda row order; verified in Phase 3b).
# ============================================================================

user_lib <- Sys.getenv("R_LIBS_USER")
if (nzchar(user_lib)) .libPaths(user_lib)
suppressMessages(library(survey))

# Resolve the project root: the dir passed as arg 1, else the working directory,
# else one level up. Run this script from the project root if in doubt.
args <- commandArgs(trailingOnly = TRUE)
root <- if (length(args) >= 1 && dir.exists(args[1])) args[1] else getwd()
if (!dir.exists(file.path(root, "data"))) root <- dirname(root)
rda_path  <- file.path(root, "data", "raw", "HINTS7_R_20250731", "hints7_public.rda")
csv_path  <- file.path(root, "data", "processed", "analysis_frame_r_export.csv")

stopifnot(file.exists(rda_path))
load(rda_path)                       # -> data.frame `public`, 7278 x 515
stopifnot(exists("public"), nrow(public) == 7278)
cat(sprintf("Loaded hints7_public.rda: %d x %d\n", nrow(public), ncol(public)))

rep_cols <- paste0("PERSON_FINWT", 1:50)

make_design <- function(df) {
  svrepdesign(
    data       = df,
    weights    = ~PERSON_FINWT0,
    repweights = df[, rep_cols],
    type       = "JKn",
    scale      = 0.98,
    rscales    = rep(1, times = 50),
    mse        = TRUE
  )
}

# ---------------------------------------------------------------------------
# Cross-check 1: published figure -- offered online access (HCP or insurer), 77%
#   Python (src/validate_harness.py): 77.19%, SE 0.934 pp, n = 7049
# ---------------------------------------------------------------------------
valid <- c("Yes", "No", "Don't know")
public$offered_either <- as.numeric(
  public$OfferedAccessHCP3 == "Yes" | public$OfferedAccessInsurer3 == "Yes"
)
public$either_valid <- (public$OfferedAccessHCP3 %in% valid) |
                       (public$OfferedAccessInsurer3 %in% valid)

des      <- make_design(public)
des_off  <- subset(des, either_valid)
m_off    <- svymean(~offered_either, des_off, deff = TRUE)

cat("\n--- Cross-check 1: offered access (HCP or insurer) ---\n")
cat(sprintf("  R survey : est = %.4f%%   SE = %.4f pp   DEff = %.3f   n = %d\n",
            coef(m_off) * 100, SE(m_off) * 100, deff(m_off), nrow(des_off)))
cat("  Python   : est = 77.1900%   SE = 0.9340 pp   DEff = 3.492   n = 7049\n")
cat("  Published: 77%\n")

# ---------------------------------------------------------------------------
# Cross-check 2: the per-respondent RATE estimator the analysis actually calls
#   Python: A 1.3935% SE 0.05627 pp DEff 1.561 | C 0.36060% SE 0.01601 pp DEff 1.441
#           B (web) 5.4827% SE 0.4638 pp DEff 2.927
# ---------------------------------------------------------------------------
if (file.exists(csv_path)) {
  rates <- read.csv(csv_path)
  stopifnot(nrow(rates) == nrow(public))           # row-order join
  public$family_a_rate <- rates$family_a_rate
  public$family_c_rate <- rates$family_c_rate
  public$family_b_rate <- rates$family_b_rate      # NA for paper respondents

  des2 <- make_design(public)
  cat("\n--- Cross-check 2: per-respondent rate estimator (weighted mean) ---\n")
  for (v in c("family_a_rate", "family_c_rate", "family_b_rate")) {
    mm <- svymean(as.formula(paste0("~", v)), des2, na.rm = TRUE, deff = TRUE)
    cat(sprintf("  %-14s R: est = %.5f%%   SE = %.5f pp   DEff = %.3f\n",
                v, coef(mm) * 100, SE(mm) * 100, deff(mm)))
  }
  cat("  Python  : family_a_rate est 1.39346%  SE 0.05627 pp  DEff 1.561\n")
  cat("            family_c_rate est 0.36060%  SE 0.01601 pp  DEff 1.441\n")
  cat("            family_b_rate est 5.48270%  SE 0.46378 pp  DEff 2.927  (web only)\n")
  cat("\n  DEff here is survey::svymean's own definition (var vs var(x)/n), i.e.\n",
      "  the design effect FOR THIS ESTIMATOR, not p(1-p)/n. It should match\n",
      "  weighting.py's `design_effect` output, not `design_effect_proportion`.\n")
} else {
  cat("\n[skip] Cross-check 2: run `python src/validate_harness.py` first to write\n")
  cat("       data/processed/analysis_frame_r_export.csv, then re-run this script.\n")
}

cat("\nExpected: R and Python agree to ~1e-6 on every SE. If they do, the\n")
cat("corrected jackknife (0.98 * sum of squared deviations, no /50) is confirmed\n")
cat("in a second language and risk R8 is met.\n")
