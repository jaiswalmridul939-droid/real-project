import { Profile } from "@/lib/api";

const fields: [keyof Profile, string][] = [
  ["state", "State"], ["district", "District"], ["age", "Age"], ["gender", "Gender"],
  ["land_acres", "Land (acres)"], ["land_ownership", "Land status"], ["income_band", "Income band"],
  ["category", "Category"], ["has_bank_account", "Bank account"], ["is_woman", "Woman farmer"],
  ["crops", "Crops"], ["family_size", "Family size"], ["occupation", "Occupation"],
];

const selectOptions: Partial<Record<keyof Profile, [string, string][]>> = {
  land_ownership: [["owner", "Owner"], ["tenant", "Tenant"], ["landless", "Landless"]],
  category: [["General", "General"], ["OBC", "OBC"], ["SC", "SC"], ["ST", "ST"]],
  has_bank_account: [["true", "Yes"], ["false", "No"]],
  is_woman: [["true", "Yes"], ["false", "No"]],
};

const translatedLabels: Record<string, Record<keyof Profile, string>> = {
  mr: { state: "राज्य", district: "जिल्हा", age: "वय", gender: "लिंग", land_acres: "जमीन (एकर)", land_ownership: "जमिनीचा प्रकार", income_band: "उत्पन्न गट", category: "प्रवर्ग", has_bank_account: "बँक खाते", is_woman: "महिला शेतकरी", crops: "पिके", family_size: "कुटुंबातील सदस्य", occupation: "व्यवसाय" },
  hi: { state: "राज्य", district: "जिला", age: "उम्र", gender: "लिंग", land_acres: "जमीन (एकड़)", land_ownership: "जमीन का प्रकार", income_band: "आय वर्ग", category: "श्रेणी", has_bank_account: "बैंक खाता", is_woman: "महिला किसान", crops: "फसलें", family_size: "परिवार के सदस्य", occupation: "पेशा" },
};

export function ProfileEditor({ profile, language, onChange }: { profile: Profile; language: "en" | "mr" | "hi"; onChange: (field: keyof Profile, value: Profile[keyof Profile]) => void }) {
  return <div className="profile-grid">{fields.map(([field, label]) => {
    const options = selectOptions[field];
    const value = profile[field];
    if (options) {
      return <label key={field}>{translatedLabels[language]?.[field] ?? label}<select value={value == null ? "" : String(value)} onChange={(event) => {
        const selected = event.target.value;
        onChange(field, selected === "" ? null : field === "has_bank_account" || field === "is_woman" ? selected === "true" : selected);
      }}><option value="">Not sure</option>{options.map(([option, text]) => <option value={option} key={option}>{text}</option>)}</select></label>;
    }
    const numeric = field === "age" || field === "land_acres" || field === "family_size";
    const valueText = Array.isArray(value) ? value.join(", ") : value == null ? "" : String(value);
    return <label key={field}>{translatedLabels[language]?.[field] ?? label}<input type={numeric ? "number" : "text"} min={numeric ? 0 : undefined} value={valueText} onChange={(event) => {
      const next = numeric ? event.target.value ? Number(event.target.value) : null : field === "crops" ? event.target.value.split(",").map((crop) => crop.trim()).filter(Boolean) : event.target.value;
      onChange(field, next);
    }} /></label>;
  })}</div>;
}