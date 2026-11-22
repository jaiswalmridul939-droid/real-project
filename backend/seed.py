from datetime import date

from sqlalchemy import select

from app.core.database import SessionLocal
from app.models import Profile, Scheme, SchemeDocument, SchemeRule, SchemeStep

SOURCE_CHECK_DATE = date(2026, 11, 21)
UNVERIFIED_DATE = date(2000, 1, 1)

# Every entry is synthetic demo data. A source URL check does not confirm eligibility criteria or deadlines.
SCHEMES = [
    {
        "name_en": "PM-KISAN Samman Nidhi", "name_mr": "पीएम-किसान सन्मान निधी", "name_hi": "पीएम-किसान सम्मान निधि",
        "description_en": "Income support for eligible landholding farmer families.", "department": "Department of Agriculture and Farmers Welfare", "level": "central",
        "benefit_summary": "Direct income support; amount and instalments are subject to current official rules.",
        "official_url": "https://pmkisan.gov.in/", "source_name": "PM-KISAN official portal",  # Source page checked 21 Nov 2026; demo rules/deadlines still require confirmation.
        "rules": [("land_ownership", "eq", "owner", "Landholding status is reported as owner."), ("state", "eq", "Maharashtra", "Applicant reports Maharashtra as their state.")],
        "docs": [("7/12 land record", "Obtain from the state land records portal or Talathi office."), ("Bank passbook", "Obtain from your bank branch."), ("Landholding details", "Check the current scheme portal requirements.")],
        "steps": [("Check current eligibility and exclusions on the official portal.", "https://pmkisan.gov.in/"), ("Complete registration or correction using the official process.", "https://pmkisan.gov.in/")],
    },
    {
        "name_en": "Namo Shetkari Mahasanman Nidhi", "name_mr": "नमो शेतकरी महासन्मान निधी", "name_hi": "नमो शेतकरी महासम्मान निधि",
        "description_en": "Maharashtra farmer support linked to the applicable state program rules.", "department": "Government of Maharashtra", "level": "state",
        "benefit_summary": "State income support, subject to current eligibility and enrollment rules.",
        "official_url": "https://nsmny.mahait.org/", "source_name": "Maharashtra Namo Shetkari portal",  # VERIFY BEFORE DEMO: source retrieval was blocked; keep its date unverified.
        "last_verified_date": UNVERIFIED_DATE,
        "rules": [("state", "eq", "Maharashtra", "Applicant reports Maharashtra as their state."), ("land_ownership", "eq", "owner", "Landholding status is reported as owner.")],
        "docs": [("7/12 land record", "Obtain from the state land records portal or Talathi office."), ("Bank passbook", "Obtain from your bank branch.")],
        "steps": [("Review the current state program notice and eligibility.", "https://nsmny.mahait.org/"), ("Check beneficiary or registration status using the official portal.", "https://nsmny.mahait.org/")],
    },
    {
        "name_en": "Pradhan Mantri Fasal Bima Yojana", "name_mr": "प्रधानमंत्री पीक विमा योजना", "name_hi": "प्रधानमंत्री फसल बीमा योजना",
        "description_en": "Crop insurance for notified crops and areas during eligible enrollment periods.", "department": "Department of Agriculture and Farmers Welfare", "level": "central",
        "benefit_summary": "Insurance protection for notified crop risks; availability depends on season, crop and location.",
        "official_url": "https://pmfby.gov.in/", "source_name": "PMFBY official portal",  # Source page checked 21 Nov 2026; demo rules/deadlines still require confirmation.
        "rules": [("state", "eq", "Maharashtra", "Applicant reports Maharashtra as their state.")],
        "docs": [("Land or tenancy proof", "Ask the Talathi or agriculture office which proof is accepted."), ("Bank passbook", "Obtain from your bank branch."), ("Sowing details", "Keep crop and season details available.")],
        "steps": [("Check whether your crop, area and season are notified.", "https://pmfby.gov.in/"), ("Apply within the active enrollment window through an authorised channel.", "https://pmfby.gov.in/")],
    },
    {
        "name_en": "Kisan Credit Card", "name_mr": "किसान क्रेडिट कार्ड", "name_hi": "किसान क्रेडिट कार्ड",
        "description_en": "Credit facility for eligible farmers, assessed by participating lenders.", "department": "Ministry of Finance and participating banks", "level": "central",
        "benefit_summary": "Access to agricultural credit subject to lender assessment and current terms.",
        "official_url": "https://www.myscheme.gov.in/schemes/kcc", "source_name": "myScheme / participating bank",  # Source page checked 21 Nov 2026; demo rules/deadlines still require confirmation.
        "rules": [("occupation", "contains", "farmer", "Applicant reports farming as an occupation.")],
        "docs": [("Land or cultivation proof", "Ask the bank which ownership or tenancy documents it accepts."), ("Bank passbook", "Obtain from your bank branch."), ("Crop plan", "Prepare expected crops and seasonal needs.")],
        "steps": [("Ask a participating bank about its KCC application and current terms.", "https://www.myscheme.gov.in/schemes/kcc"), ("Submit the bank's requested documents for assessment.", "https://www.myscheme.gov.in/schemes/kcc")],
    },
    {
        "name_en": "Soil Health Card Scheme", "name_mr": "मृदा आरोग्य पत्रिका योजना", "name_hi": "मृदा स्वास्थ्य कार्ड योजना",
        "description_en": "Soil testing and nutrient recommendations through the agriculture extension system.", "department": "Department of Agriculture and Farmers Welfare", "level": "central",
        "benefit_summary": "Soil test information and crop-specific nutrient guidance; contact the local agriculture office.",
        "official_url": "https://soilhealth.dac.gov.in/", "source_name": "Soil Health Card portal",  # Source page checked 21 Nov 2026; demo rules/deadlines still require confirmation.
        "rules": [("state", "eq", "Maharashtra", "Applicant reports Maharashtra as their state.")],
        "docs": [("Land details", "Ask the local agriculture office what plot details are needed.")],
        "steps": [("Contact the local Krishi office about soil sampling.", "https://soilhealth.dac.gov.in/"), ("Use the portal to view available soil health information.", "https://soilhealth.dac.gov.in/")],
    },
    {
        "name_en": "PM-KUSUM", "name_mr": "पीएम-कुसुम", "name_hi": "पीएम-कुसुम",
        "description_en": "Support for eligible decentralised solar energy installations under active components.", "department": "Ministry of New and Renewable Energy", "level": "central",
        "benefit_summary": "Component-specific support; applications depend on state capacity and current calls.",
        "official_url": "https://pmkusum.mnre.gov.in/", "source_name": "MNRE PM-KUSUM portal",  # Source page checked 21 Nov 2026; demo rules/deadlines still require confirmation.
        "rules": [("state", "eq", "Maharashtra", "Applicant reports Maharashtra as their state.")],
        "docs": [("Land and pump details", "Ask the state implementing agency what site details are required."), ("Bank passbook", "Obtain from your bank branch.")],
        "steps": [("Check active components and Maharashtra application status.", "https://pmkusum.mnre.gov.in/"), ("Apply only through the state-designated process when open.", "https://pmkusum.mnre.gov.in/")],
    },
    {
        "name_en": "PM Krishi Sinchayee Yojana - Per Drop More Crop", "name_mr": "प्रधानमंत्री कृषी सिंचन योजना - प्रति थेंब अधिक पीक", "name_hi": "प्रधानमंत्री कृषि सिंचाई योजना - प्रति बूंद अधिक फसल",
        "description_en": "Micro-irrigation support through state implementation and active application windows.", "department": "Department of Agriculture and Farmers Welfare", "level": "central",
        "benefit_summary": "Potential assistance for eligible micro-irrigation systems; rates and availability vary.",
        "official_url": "https://pmksy.gov.in/", "source_name": "PMKSY official portal",  # VERIFY BEFORE DEMO: portal shows a 2019 update; keep its date unverified.
        "last_verified_date": UNVERIFIED_DATE,
        "rules": [("state", "eq", "Maharashtra", "Applicant reports Maharashtra as their state.")],
        "docs": [("Land record", "Obtain from the state land records portal or Talathi office."), ("Water source details", "Ask the agriculture office about accepted evidence.")],
        "steps": [("Ask the district agriculture office about the current micro-irrigation window.", "https://pmksy.gov.in/"), ("Confirm eligible equipment and assistance before purchase.", "https://pmksy.gov.in/")],
    },
    {
        "name_en": "Agriculture Infrastructure Fund", "name_mr": "कृषी पायाभूत सुविधा निधी", "name_hi": "कृषि अवसंरचना कोष",
        "description_en": "Financing support for eligible agriculture infrastructure projects.", "department": "Department of Agriculture and Farmers Welfare", "level": "central",
        "benefit_summary": "Financing terms and eligibility depend on project type and lender assessment.",
        "official_url": "https://agriinfra.dac.gov.in/", "source_name": "Agriculture Infrastructure Fund portal",  # Source page checked 21 Nov 2026; demo rules/deadlines still require confirmation.
        "rules": [("occupation", "contains", "farmer", "Applicant reports farming as an occupation.")],
        "docs": [("Project plan", "Prepare a project proposal and cost estimate."), ("Bank documents", "Ask a participating lender for its current checklist.")],
        "steps": [("Review eligible project types on the official portal.", "https://agriinfra.dac.gov.in/"), ("Discuss financing with a participating lender.", "https://agriinfra.dac.gov.in/")],
    },
    {
        "name_en": "Dr. Babasaheb Ambedkar Krishi Swavalamban Yojana", "name_mr": "डॉ. बाबासाहेब आंबेडकर कृषी स्वावलंबन योजना", "name_hi": "डॉ. बाबासाहेब आंबेडकर कृषि स्वावलंबन योजना",
        "description_en": "Maharashtra agriculture support for eligible applicant groups under current state rules.", "department": "Government of Maharashtra", "level": "state",
        "benefit_summary": "Component-specific agricultural support; eligibility must be checked with the state authority.",
        "official_url": "https://mahadbt.maharashtra.gov.in/", "source_name": "MahaDBT Farmer portal",  # Source listing checked 21 Nov 2026; demo rules/deadlines still require confirmation.
        "rules": [("state", "eq", "Maharashtra", "Applicant reports Maharashtra as their state."), ("category", "eq", "SC", "Applicant reports Scheduled Caste category; verify current program criteria.")],
        "docs": [("Caste certificate", "Obtain from the competent revenue authority."), ("Land record", "Obtain from the state land records portal or Talathi office."), ("Income certificate", "Ask the Tehsil office about the current process.")],
        "steps": [("Check the current scheme listing and eligibility on MahaDBT.", "https://mahadbt.maharashtra.gov.in/"), ("Confirm documents and application dates with the agriculture office.", "https://mahadbt.maharashtra.gov.in/")],
    },
    {
        "name_en": "Birsa Munda Krishi Kranti Yojana", "name_mr": "बिरसा मुंडा कृषी क्रांती योजना", "name_hi": "बिरसा मुंडा कृषि क्रांति योजना",
        "description_en": "Maharashtra agriculture support for eligible applicant groups under current state rules.", "department": "Government of Maharashtra", "level": "state",
        "benefit_summary": "Component-specific agricultural support; eligibility must be checked with the state authority.",
        "official_url": "https://mahadbt.maharashtra.gov.in/", "source_name": "MahaDBT Farmer portal",  # Source listing checked 21 Nov 2026; demo rules/deadlines still require confirmation.
        "rules": [("state", "eq", "Maharashtra", "Applicant reports Maharashtra as their state."), ("category", "eq", "ST", "Applicant reports Scheduled Tribe category; verify current program criteria.")],
        "docs": [("Caste or tribe certificate", "Obtain from the competent revenue authority."), ("Land record", "Obtain from the state land records portal or Talathi office."), ("Income certificate", "Ask the Tehsil office about the current process.")],
        "steps": [("Check the current scheme listing and eligibility on MahaDBT.", "https://mahadbt.maharashtra.gov.in/"), ("Confirm documents and application dates with the agriculture office.", "https://mahadbt.maharashtra.gov.in/")],
    },
]

SAMPLE_PROFILES = [
    {"state": "Maharashtra", "district": "Nashik", "age": 42, "gender": "woman", "land_acres": 2.0, "land_ownership": "owner", "income_band": "low", "category": "General", "has_bank_account": True, "is_woman": True, "crops": ["grapes", "onion"], "family_size": 4, "occupation": "farmer"},
    {"state": "Maharashtra", "district": "Pune", "age": 51, "gender": "man", "land_acres": 3.5, "land_ownership": "owner", "income_band": "middle", "category": "OBC", "has_bank_account": True, "is_woman": False, "crops": ["sugarcane"], "family_size": 5, "occupation": "farmer"},
    {"state": "Maharashtra", "district": "Nanded", "age": 36, "gender": "woman", "land_acres": 1.0, "land_ownership": "tenant", "income_band": "low", "category": "SC", "has_bank_account": True, "is_woman": True, "crops": ["cotton"], "family_size": 3, "occupation": "farmer"},
    {"state": "Maharashtra", "district": "Gadchiroli", "age": 29, "gender": "man", "land_acres": 2.5, "land_ownership": "owner", "income_band": "low", "category": "ST", "has_bank_account": False, "is_woman": False, "crops": ["paddy"], "family_size": 6, "occupation": "farmer"},
    {"state": "Maharashtra", "district": "Solapur", "age": 63, "gender": "woman", "land_acres": 0.0, "land_ownership": "landless", "income_band": "low", "category": "OBC", "has_bank_account": True, "is_woman": True, "crops": [], "family_size": 2, "occupation": "agricultural labourer"},
]


def seed() -> None:
    with SessionLocal() as db:
        for item in SCHEMES:
            scheme = db.scalar(select(Scheme).where(Scheme.name_en == item["name_en"]))
            if scheme is None:
                scheme = Scheme(
                    name_en=item["name_en"], name_mr=item["name_mr"], name_hi=item["name_hi"],
                    description_en=item["description_en"], department=item["department"], level=item["level"],
                    benefit_summary=item["benefit_summary"], official_url=item["official_url"], source_name=item["source_name"],
                    last_verified_date=item.get("last_verified_date", SOURCE_CHECK_DATE), is_active=True,
                )
                db.add(scheme)
                db.flush()
                for field, operator, value, explanation in item["rules"]:
                    db.add(SchemeRule(scheme_id=scheme.id, field=field, operator=operator, value_json=value, weight=1, explanation_en=explanation))
                for name, where in item["docs"]:
                    db.add(SchemeDocument(scheme_id=scheme.id, doc_name_en=name, where_to_get=where, is_mandatory=True))
                for number, (text, link) in enumerate(item["steps"], start=1):
                    db.add(SchemeStep(scheme_id=scheme.id, step_no=number, text_en=text, link_nullable=link))
            elif scheme.last_verified_date == UNVERIFIED_DATE:
                scheme.last_verified_date = item.get("last_verified_date", SOURCE_CHECK_DATE)
        if db.scalar(select(Profile.id).limit(1)) is None:
            db.add_all([Profile(**profile) for profile in SAMPLE_PROFILES])
        db.commit()
        print(f"Seeded or confirmed {len(SCHEMES)} schemes and 5 synthetic profiles.")


if __name__ == "__main__":
    seed()