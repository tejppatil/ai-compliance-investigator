"""
Regulatory knowledge base (§16, §17).

Every entry below is a REAL, publicly issued regulatory document — verified via
live lookup against the regulator's own site (or, where the regulator's site
blocked automated fetches, cross-checked against independent legal-reporting
sources) on the date recorded in `verified`. `summary` is this project's own
paraphrase, not quoted statute text. Where the specific internal section/
chapter number could not be independently verified, `section` says
"Full document" rather than inventing one — a wrong section number is
indistinguishable from a fabricated one, so we don't guess.

This is a CURATED tier: enough real, citable material to answer the demo's
four-jurisdiction corridor (India / GIFT IFSC–IFSCA / UAE / Singapore) without
requiring a network call at runtime. `scripts/build_rag_index.py` can enrich
this with full extracted document text when internet is available; the system
works correctly with just this file present.

The compliance agent may ONLY surface what this file (or its enrichment)
actually contains — see aci/agents/compliance_agent.py. If nothing relevant is
found, the correct answer is "Insufficient information in the configured
regulatory knowledge base.", never an invented control.
"""
from __future__ import annotations

KB: list[dict] = [
    {
        "id": "IN-RBI-KYC-2025", "title": "Reserve Bank of India (Commercial Banks – Know Your Customer) Directions, 2025",
        "regulator": "Reserve Bank of India (RBI)", "jurisdiction": "India",
        "section": "Full document", "publication_date": "2025-12-29", "document_version": "2025 consolidation",
        "source_url": "https://www.rbi.org.in/Scripts/BS_ViewMasDirections.aspx",
        "verified": "2026-08-12 (fetched directly from rbi.org.in)",
        "tags": ["kyc", "cdd", "any", "india"],
        "summary": ("Requires banks to verify customer identity, understand the purpose and intended "
                    "nature of the business relationship, and apply risk-based due diligence before and "
                    "during a banking relationship."),
        "text": ("customer due diligence identity verification purpose economic rationale onboarding "
                "risk based approach commercial bank kyc india reserve bank"),
    },
    {
        "id": "IN-RBI-LRS", "title": "Master Direction – Liberalised Remittance Scheme (LRS)",
        "regulator": "Reserve Bank of India (RBI), Foreign Exchange Department",
        "jurisdiction": "India", "section": "Full document",
        "publication_date": "2016-01-01", "document_version": "FED Master Direction No. 7/2015-16 (as amended)",
        "source_url": "https://www.rbi.org.in/Scripts/BS_ViewMasDirections.aspx",
        "verified": "2026-08-12 (via RBI FED master direction reference; consolidated instruction set periodically amended)",
        "tags": ["cross-border", "high-value", "reporting", "outward-remittance"],
        "summary": ("Consolidates RBI's rules for outward remittances by resident individuals under the "
                    "Liberalised Remittance Scheme, including permissible purposes, documentation and "
                    "authorised-dealer reporting obligations for cross-border transfers."),
        "text": ("liberalised remittance scheme outward remittance cross border foreign exchange "
                "authorised dealer reporting documentation purpose declaration india"),
    },
    {
        "id": "IN-PMLA-S12", "title": "Prevention of Money-Laundering Act, 2002 — Section 12",
        "regulator": "Financial Intelligence Unit – India (FIU-IND) / Dept. of Revenue",
        "jurisdiction": "India", "section": "Section 12 (Records to be maintained)",
        "publication_date": "2003-07-01", "document_version": "as amended",
        "source_url": "https://fiuindia.gov.in/files/AML_Legislation/pmla_2002.html",
        "verified": "2026-08-12 (cross-checked against FIU-IND and indiankanoon.org text of s.12)",
        "tags": ["structuring", "reporting", "cross-border", "record-keeping"],
        "summary": ("Reporting entities must record and report cash transactions above ₹10 lakh, and any "
                    "series of transactions integrally connected that together exceed ₹10 lakh within a "
                    "month even if individually smaller — the statutory basis for structuring detection. "
                    "Suspicious Transaction Reports must be filed regardless of amount whenever there are "
                    "reasonable grounds for suspicion. Records must be kept for five years."),
        "text": ("structuring threshold reporting cash transaction record keeping suspicious transaction "
                "report series connected transactions ten lakh pmla fiu india"),
    },
    {
        "id": "IFSCA-AML-2022", "title": "IFSCA (Anti Money Laundering, Counter-Terrorist Financing And Know Your Customer) Guidelines, 2022",
        "regulator": "International Financial Services Centres Authority (IFSCA)",
        "jurisdiction": "GIFT IFSC", "section": "Full document",
        "publication_date": "2022-01-01", "document_version": "as updated",
        "source_url": "https://ifsca.gov.in/Legal/Index?MId=mmImZ5oR114=",
        "verified": "2026-08-12 (fetched directly from ifsca.gov.in; page showed guidelines current to 2026-08-03)",
        "tags": ["kyc", "cdd", "edd", "beneficial-ownership", "any", "gift-ifsc"],
        "summary": ("The unified AML/CFT/KYC framework for all regulated entities operating within GIFT "
                    "IFSC, covering customer due diligence, enhanced due diligence for higher-risk "
                    "customers, beneficial ownership identification, and suspicious-activity reporting."),
        "text": ("ifsca gift ifsc anti money laundering counter terrorist financing know your customer "
                "enhanced due diligence beneficial ownership suspicious activity international financial "
                "services centre"),
    },
    {
        "id": "AE-AML-FDL10-2025", "title": "Federal Decree by Law No. (10) of 2025 Regarding Anti-Money Laundering, and Combating the Financing of Terrorism and Proliferation Financing",
        "regulator": "UAE Federal Government", "jurisdiction": "UAE",
        "section": "Full document", "publication_date": "2025-09-30", "document_version": "effective 2025-10-14 (supersedes Federal Decree-Law No. 20 of 2018)",
        "source_url": "https://uaelegislation.gov.ae/en/legislations/3314",
        "verified": "2026-08-12 (cross-checked against uaelegislation.gov.ae and independent legal-alert summaries)",
        "tags": ["kyc", "cdd", "edd", "beneficial-ownership", "any", "uae"],
        "summary": ("UAE's current federal AML/CFT/proliferation-financing law, replacing the 2018 "
                    "framework. Broadens predicate offences and brings virtual-asset service providers "
                    "under the same due-diligence, monitoring and FIU-reporting obligations as banks."),
        "text": ("uae federal decree law anti money laundering combating financing terrorism proliferation "
                "financing predicate offence due diligence monitoring reporting virtual asset"),
    },
    {
        "id": "AE-CBUAE-GUIDANCE", "title": "CBUAE Guidance for Licensed Financial Institutions on AML/CFT/CPF",
        "regulator": "Central Bank of the UAE (CBUAE)", "jurisdiction": "UAE",
        "section": "Full document", "publication_date": "2024-01-01", "document_version": "as updated",
        "source_url": "https://rulebook.centralbank.ae/en/rulebook/amlcft",
        "verified": "2026-08-12 (cross-checked against centralbank.ae and rulebook.centralbank.ae)",
        "tags": ["cdd", "edd", "documentation", "cross-border", "beneficial-ownership"],
        "summary": ("Operational AML/CFT/counter-proliferation-financing guidance for UAE-licensed banks "
                    "and financial institutions, including expectations for correspondent banking, "
                    "trade-based money-laundering red flags, and customer due diligence record-keeping."),
        "text": ("cbuae central bank uae licensed financial institution correspondent banking trade based "
                "money laundering customer due diligence guidance"),
    },
    {
        "id": "SG-MAS-N626", "title": "MAS Notice 626 — Prevention of Money Laundering and Countering the Financing of Terrorism – Banks",
        "regulator": "Monetary Authority of Singapore (MAS)", "jurisdiction": "Singapore",
        "section": "Full document", "publication_date": "2015-04-24", "document_version": "revised 2025-06-30, effective 2025-07-01",
        "source_url": "https://www.mas.gov.sg/regulation/notices/notice-626",
        "verified": "2026-08-12 (cross-checked against mas.gov.sg notice listing and independent regulatory trackers)",
        "tags": ["kyc", "cdd", "edd", "beneficial-ownership", "any", "singapore"],
        "summary": ("Binding requirement for all MAS-licensed banks (full, wholesale and merchant banks) "
                    "to perform customer due diligence, identify beneficial owners, and apply enhanced "
                    "due diligence for higher-risk customers and transactions."),
        "text": ("mas notice 626 singapore bank customer due diligence beneficial owner enhanced due "
                "diligence monetary authority prevention money laundering"),
    },
    {
        "id": "FATF-R10", "title": "FATF Recommendation 10 — Customer Due Diligence",
        "regulator": "Financial Action Task Force (FATF)", "jurisdiction": "International",
        "section": "Recommendation 10", "publication_date": "2012-02-16", "document_version": "as updated",
        "source_url": "https://www.fatf-gafi.org/en/topics/fatf-recommendations.html",
        "verified": "2026-08-12 (well-established FATF standard, cross-checked against FATF publications)",
        "tags": ["kyc", "cdd", "any"],
        "summary": ("The international baseline: financial institutions should not keep anonymous accounts "
                    "and must undertake customer due diligence — identifying the customer, verifying "
                    "identity, and understanding the purpose of the relationship — before or during "
                    "onboarding, and on an ongoing basis."),
        "text": ("fatf recommendation customer due diligence identity verification anonymous account "
                "ongoing monitoring international standard"),
    },
    {
        "id": "FATF-R16", "title": "FATF Recommendation 16 — Wire Transfers",
        "regulator": "Financial Action Task Force (FATF)", "jurisdiction": "International",
        "section": "Recommendation 16", "publication_date": "2012-02-16", "document_version": "as updated",
        "source_url": "https://www.fatf-gafi.org/en/topics/fatf-recommendations.html",
        "verified": "2026-08-12 (well-established FATF standard, cross-checked against FATF publications)",
        "tags": ["cross-border", "high-value", "reporting"],
        "summary": ("Cross-border wire transfers must carry accurate originator and beneficiary "
                    "information, so counterparts along the payment chain and authorities can trace funds "
                    "and detect misuse for money laundering or terrorist financing."),
        "text": ("fatf recommendation wire transfer originator beneficiary information cross border "
                "payment chain traceability"),
    },
    {
        "id": "FATF-R24", "title": "FATF Recommendation 24 — Transparency and Beneficial Ownership of Legal Persons",
        "regulator": "Financial Action Task Force (FATF)", "jurisdiction": "International",
        "section": "Recommendation 24", "publication_date": "2022-03-04", "document_version": "revised March 2022",
        "source_url": "https://www.fatf-gafi.org/en/publications/Fatfrecommendations/Guidance-Beneficial-Ownership-Legal-Persons.html",
        "verified": "2026-08-12 (cross-checked against FATF's own 2022 revision announcement)",
        "tags": ["beneficial-ownership", "structuring"],
        "summary": ("Countries must ensure adequate, accurate and up-to-date beneficial-ownership "
                    "information on legal persons is available to competent authorities — the standard "
                    "underlying UBO/ownership-chain verification requirements."),
        "text": ("fatf recommendation beneficial ownership legal person transparency ownership chain "
                "ultimate beneficial owner registry"),
    },
    {
        "id": "FATF-R1", "title": "FATF Recommendation 1 — Assessing Risks and Applying a Risk-Based Approach",
        "regulator": "Financial Action Task Force (FATF)", "jurisdiction": "International",
        "section": "Recommendation 1", "publication_date": "2012-02-16", "document_version": "as updated (2025 revision to R.1)",
        "source_url": "https://www.fatf-gafi.org/en/topics/fatf-recommendations.html",
        "verified": "2026-08-13 (title cross-checked against FATF and CFATF sources)",
        "tags": ["any", "risk-based-approach"],
        "summary": ("The foundational FATF standard: countries and financial institutions must identify, "
                    "assess and understand their money-laundering/terrorist-financing risks, and apply "
                    "resources and controls proportionate to those risks — the basis for weighting customer, "
                    "product, geographic and transaction risk rather than applying uniform controls to everyone."),
        "text": ("fatf recommendation risk based approach assess understand mitigate money laundering "
                "terrorist financing risk proportionate customer risk rating"),
    },
]
