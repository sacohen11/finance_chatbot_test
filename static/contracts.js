const fieldIds = [
  "planned_spend",
  "actual_spend",
  "planned_labor_hours",
  "actual_labor_hours",
  "notes",
];

function showFeedback(message, type = "info") {
  const box = document.getElementById("feedback");
  box.textContent = message;
  box.className = `feedback ${type}`;
  box.style.display = "block";
}

function getFormData() {
  return {
    contract_number: document.getElementById("contract_number").value.trim(),
    report_month: document.getElementById("report_month").value,
    planned_spend: document.getElementById("planned_spend").value,
    actual_spend: document.getElementById("actual_spend").value,
    planned_labor_hours: document.getElementById("planned_labor_hours").value,
    actual_labor_hours: document.getElementById("actual_labor_hours").value,
    notes: document.getElementById("notes").value,
  };
}

function fillReport(report) {
  if (!report) return;
  for (const id of fieldIds) {
    const el = document.getElementById(id);
    el.value = report[id] ?? "";
  }
}

async function lookupReport() {
  const contractNumber = document.getElementById("contract_number").value.trim();
  const reportMonth = document.getElementById("report_month").value;

  if (!contractNumber || !reportMonth) {
    showFeedback("Contract number and month are required for lookup", "error");
    return;
  }

  try {
    const resp = await fetch(`/api/contracts/${encodeURIComponent(contractNumber)}/reports?month=${encodeURIComponent(reportMonth)}`);
    const data = await resp.json();

    if (!resp.ok) {
      if (resp.status === 404) {
        showFeedback("No historical data found for contract", "info");
        return;
      }
      throw new Error(data.error || "Lookup failed");
    }

    fillReport(data.report);

    if (data.source === "prior") {
      showFeedback("Loaded prior month data", "info");
    } else {
      showFeedback("Loaded exact month data", "info");
    }
  } catch (error) {
    showFeedback(error.message, "error");
  }
}

async function saveReport() {
  const payload = getFormData();

  try {
    const resp = await fetch("/api/reports", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await resp.json();

    if (!resp.ok) {
      throw new Error(data.error || "Save failed");
    }

    showFeedback("Saved successfully", "success");
  } catch (error) {
    showFeedback(error.message, "error");
  }
}

document.getElementById("lookup_btn").addEventListener("click", lookupReport);
document.getElementById("save_btn").addEventListener("click", saveReport);
