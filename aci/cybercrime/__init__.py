"""
Cyber Crime & Financial Fraud Investigation module — bolted onto the AI
Compliance Investigator (see aci/ for the GIFT IFSC corporate-AML side).

Different domain, different users: this module is for a law-enforcement /
bank fraud-cell workflow (live transaction monitoring, mule-account layering,
geographic incident intelligence, multi-officer case ownership) rather than
the corporate cross-border compliance case files the rest of this project
investigates. It shares this project's non-negotiables — deterministic rule
logic (nothing here is an LLM judgment call), synthetic data only, and a
human always makes the final call (the "freeze" action is an officer's
button, never something the rule engine does on its own) — but is otherwise
a self-contained package so the two domains don't get tangled.
"""
