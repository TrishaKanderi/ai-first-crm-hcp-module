Regression check for the AIVOA HCP CRM agent.
Run from the backend/ folder with GROQ_API_KEY set (pip install -r requirements.txt first):
  python ../regression_check/run_eval.py --label v1_first_prompt
  python ../regression_check/run_eval.py --label v2_current --baseline results_v1_first_prompt.json
Scores 19 fixed cases (8 extraction, 6 compliance, 5 tool routing) with deterministic rules; exits 1 on any regression.
