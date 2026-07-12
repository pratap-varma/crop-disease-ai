// ===============================
// DOM Elements
// ===============================

const uploadForm = document.getElementById("uploadForm");
const imageInput = document.getElementById("imageInput");
const previewImage = document.getElementById("previewImage");
const loading = document.getElementById("loading");
const resultSection = document.getElementById("resultSection");
const dropArea = document.getElementById("dropArea");

// ===============================
// Drag & Drop
// ===============================

dropArea.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropArea.classList.add("dragover");
});

dropArea.addEventListener("dragleave", () => {
    dropArea.classList.remove("dragover");
});

dropArea.addEventListener("drop", (e) => {
    e.preventDefault();
    dropArea.classList.remove("dragover");

    if (e.dataTransfer.files.length > 0) {
        imageInput.files = e.dataTransfer.files;
        showPreview(imageInput.files[0]);
    }
});

dropArea.addEventListener("click", () => {
    imageInput.click();
});

// ===============================
// Preview Image
// ===============================

imageInput.addEventListener("change", () => {

    if (imageInput.files.length > 0) {

        showPreview(imageInput.files[0]);

    }

});

function showPreview(file){

    const reader = new FileReader();

    reader.onload = function(e){

        previewImage.src = e.target.result;

        previewImage.classList.remove("hidden");

    }

    reader.readAsDataURL(file);

}

// ===============================
// Upload Image
// ===============================

// Global state variables for voice and PDF export
let currentResult = null;
let currentTreatment = null;
let speechUtterance = null;
let isSpeaking = false;

uploadForm.addEventListener("submit", async function(e){

    e.preventDefault();

    if(imageInput.files.length===0){

        alert("Please select an image.");

        return;

    }

    // Cancel any active Speech Synthesis
    if (window.speechSynthesis) {
        window.speechSynthesis.cancel();
    }
    resetSpeechButton();

    loading.classList.remove("hidden");

    resultSection.classList.add("hidden");

    const formData=new FormData();

    formData.append("image",imageInput.files[0]);

    try{

        const response=await fetch("/predict",{

            method:"POST",

            body:formData

        });

        const data=await response.json();

        loading.classList.add("hidden");

        if(!data.success){

            alert(data.message);

            return;

        }

        displayResult(data.result, data.treatment_guidance);

    }

    catch(error){

        loading.classList.add("hidden");

        alert("Server Error.");

        console.error(error);

    }

});

// ===============================
// Display Result
// ===============================

function displayResult(result, treatmentGuidance){

    resultSection.classList.remove("hidden");

    // Store in global state
    currentResult = result;
    currentTreatment = treatmentGuidance;

    // Set AI results
    document.getElementById("cropName").textContent=result.crop_name;

    document.getElementById("diseaseName").textContent=result.disease_name;

    document.getElementById("confidence").textContent=result.confidence;

    document.getElementById("severity").textContent=result.severity;

    document.getElementById("fertilizer").textContent=result.fertilizer_recommendation;

    document.getElementById("watering").textContent=result.watering_advice;

    document.getElementById("notes").textContent=result.additional_notes;

    populateList("symptoms",result.symptoms);

    populateList("causes",result.possible_causes);

    populateList("prevention",result.prevention);

    populateList("treatment",result.treatment);

    // ===============================
    // Render Treatment Guidance
    // ===============================
    const treatmentSection = document.getElementById("treatmentGuidanceSection");
    const treatmentVerified = document.getElementById("treatmentVerified");
    const treatmentFallback = document.getElementById("treatmentFallback");

    if (treatmentSection) {
        treatmentSection.classList.remove("hidden");

        if (treatmentGuidance) {
            // Show verified, hide fallback
            treatmentVerified.classList.remove("hidden");
            treatmentFallback.classList.add("hidden");

            // 1. Organic Treatment
            const organicSteps = document.getElementById("organicSteps");
            organicSteps.innerHTML = "";
            if (treatmentGuidance.organic_treatment && treatmentGuidance.organic_treatment.length > 0) {
                treatmentGuidance.organic_treatment.forEach((step, idx) => {
                    const stepDiv = document.createElement("div");
                    stepDiv.className = "flex flex-col mb-4";
                    stepDiv.innerHTML = `
                        <span class="text-xs font-bold text-green-700 uppercase tracking-wider mb-1">Step ${idx + 1}</span>
                        <p class="text-xs text-gray-700 font-medium leading-relaxed">${step}</p>
                    `;
                    organicSteps.appendChild(stepDiv);
                });
            }
            document.getElementById("organicAlt").textContent = treatmentGuidance.alternative_organic_solutions || "None";

            // 2. Chemical Treatment
            document.getElementById("chemicalName").textContent = treatmentGuidance.chemical_treatment_name;
            document.getElementById("activeIngredient").textContent = treatmentGuidance.active_ingredient;
            document.getElementById("chemicalPurpose").textContent = treatmentGuidance.purpose;
            document.getElementById("brandNames").textContent = treatmentGuidance.example_brand_names;

            // 3. Mixing Guide & Sprayer Calculator Setup
            // Reset Sprayer & Land Calculator Controls
            const landSizeInput = document.getElementById("landSizeInput");
            const landUnitSelect = document.getElementById("landUnitSelect");
            const typeSelect = document.getElementById("sprayerTypeSelect");
            const capacityInput = document.getElementById("sprayerCapacityInput");
            if (landSizeInput && landUnitSelect && typeSelect && capacityInput) {
                landSizeInput.value = 1;
                landUnitSelect.value = "acres";
                typeSelect.value = "knapsack";
                capacityInput.value = 15;
                capacityInput.readOnly = true;
                capacityInput.classList.add("cursor-not-allowed");
            }
            
            // Run Sprayer Calculations to populate mixing quantities, steps, and costs
            updateSprayerCalculations();

            // 4. Application Guide
            const appChecklist = document.getElementById("applicationChecklist");
            appChecklist.innerHTML = "";
            const sprayLocations = ["Upper surface of leaves", "Lower surface of leaves", "Stem", "Around infected area"];
            sprayLocations.forEach(loc => {
                const isChecked = treatmentGuidance.where_to_spray && treatmentGuidance.where_to_spray.includes(loc);
                const item = document.createElement("div");
                item.className = "flex items-center space-x-2 text-xs font-semibold " + (isChecked ? "text-green-700" : "text-gray-400 line-through");
                item.innerHTML = isChecked 
                    ? `<span class="text-green-600 text-sm font-bold">✔</span> <span>${loc}</span>`
                    : `<span class="text-gray-300 text-sm font-bold">✕</span> <span>${loc}</span>`;
                appChecklist.appendChild(item);
            });

            // 5. Best Time to Spray: मॉर्निंग / इवनिंग details are structured in HTML. No dynamic injection needed unless interval changes.

            // 6. Repeat Schedule
            document.getElementById("repeatInterval").textContent = treatmentGuidance.spray_interval;
            document.getElementById("repeatMax").textContent = `${treatmentGuidance.number_of_applications} Applications`;

            const timeline = document.getElementById("repeatTimeline");
            timeline.innerHTML = "";
            const maxApps = treatment_guidance_max_apps = treatmentGuidance.number_of_applications || 3;
            const daysInterval = parseInt(treatmentGuidance.spray_interval) || 7;
            for (let i = 1; i <= maxApps; i++) {
                const day = (i - 1) * daysInterval + 1;
                
                // Add Circle Node
                const node = document.createElement("div");
                node.className = "text-center relative z-10";
                node.innerHTML = `
                    <div class="w-8 h-8 rounded-full bg-green-100 border-2 border-green-500 flex items-center justify-center mx-auto text-xs font-black text-green-700">
                        ${i}
                    </div>
                    <span class="block text-[10px] text-gray-500 mt-1 font-bold">Day ${day}</span>
                `;
                timeline.appendChild(node);

                // Add Connector Line
                if (i < maxApps) {
                    const line = document.createElement("div");
                    line.className = "flex-grow border-t-2 border-dashed border-green-300 mx-2 -mt-4";
                    timeline.appendChild(line);
                }
            }

            // 7. Safety & PPE
            const ppeList = document.getElementById("ppeList");
            ppeList.innerHTML = "";
            if (treatmentGuidance.ppe_required) {
                treatmentGuidance.ppe_required.split(",").forEach(ppe => {
                    const badge = document.createElement("span");
                    badge.className = "px-3 py-1.5 bg-red-50 text-red-700 border border-red-200/50 rounded-xl text-xs font-bold shadow-sm";
                    badge.textContent = ppe.trim();
                    ppeList.appendChild(badge);
                });
            }

            // 8. Things To Avoid
            const avoidRules = document.getElementById("avoidRules");
            avoidRules.innerHTML = "";
            const avoidItems = [
                "Do not overuse medicine.",
                "Do not mix chemicals randomly.",
                "Do not spray before rainfall.",
                "Do not exceed dosage."
            ];
            avoidItems.forEach(item => {
                const li = document.createElement("li");
                li.className = "flex items-center space-x-3 text-xs text-red-800";
                li.innerHTML = `
                    <span class="text-red-500 font-bold text-sm shrink-0">✕</span>
                    <span>${item}</span>
                `;
                avoidRules.appendChild(li);
            });

            // Footer
            document.getElementById("govAdvisory").textContent = treatmentGuidance.government_advisory_source || "State Agricultural Department";
            document.getElementById("lastUpdated").textContent = treatmentGuidance.last_updated_date || "2026-07-12";

        } else {
            // Show fallback, hide verified
            treatmentVerified.classList.add("hidden");
            treatmentFallback.classList.remove("hidden");
        }
    }

    resultSection.scrollIntoView({

        behavior:"smooth"

    });

}

// ===============================
// Populate UL Lists
// ===============================

function populateList(id,array){

    const ul=document.getElementById(id);

    ul.innerHTML="";

    if(!array || array.length===0){

        const li=document.createElement("li");

        li.innerText="No information available.";

        ul.appendChild(li);

        return;

    }

    array.forEach(item=>{

        const li=document.createElement("li");

        li.innerText=item;

        ul.appendChild(li);

    });

}

// ===============================
// Text-to-Speech (Voice Feature)
// ===============================

function resetSpeechButton() {
    isSpeaking = false;
    const ttsIcon = document.getElementById("ttsIcon");
    const ttsText = document.getElementById("ttsText");
    if (ttsIcon && ttsText) {
        ttsIcon.className = "fas fa-volume-up";
        ttsText.textContent = "Listen Report";
    }
}

function toggleSpeech() {
    if (!currentResult) return;
    
    if (isSpeaking) {
        window.speechSynthesis.cancel();
        resetSpeechButton();
        return;
    }
    
    let textToRead = `Crop Disease Report. Crop analyzed is ${currentResult.crop_name}. `;
    textToRead += `Disease identified is ${currentResult.disease_name}. `;
    textToRead += `Confidence level is ${currentResult.confidence}. Severity is ${currentResult.severity}. `;
    
    if (currentResult.symptoms && currentResult.symptoms.length > 0) {
        textToRead += `Symptoms observed: ${currentResult.symptoms.join(". ")}. `;
    }
    
    if (currentResult.possible_causes && currentResult.possible_causes.length > 0) {
        textToRead += `Causes: ${currentResult.possible_causes.join(". ")}. `;
    }
    
    if (currentTreatment) {
        textToRead += `Verified Treatment Guidance: `;
        if (currentTreatment.organic_treatment && currentTreatment.organic_treatment.length > 0) {
            textToRead += `Organic steps include: `;
            currentTreatment.organic_treatment.forEach((step, idx) => {
                textToRead += `Step ${idx + 1}: ${step}. `;
            });
        }
        textToRead += `Chemical medicine name is ${currentTreatment.chemical_treatment_name}. `;
        textToRead += `Active ingredient is ${currentTreatment.active_ingredient}. `;
        
        // Read sprayer calculator metrics
        const landSize = document.getElementById("landSizeInput").value;
        const landUnit = document.getElementById("landUnitSelect").value;
        const totalMed = document.getElementById("mixingMedicine").textContent;
        const totalWater = document.getElementById("mixingWater").textContent;
        const tanksCount = document.getElementById("tanksCount").textContent;
        const perTankDosage = document.getElementById("perTankDosage").textContent;
        const totalCost = document.getElementById("costTotal").textContent;

        textToRead += `For a land size of ${landSize} ${landUnit}, the total field medicine required is ${totalMed} dissolved in ${totalWater} of water. `;
        textToRead += `This will require ${tanksCount}. `;
        textToRead += `For each tank run, mix ${perTankDosage}. `;
        textToRead += `The estimated total field treatment cost is ${totalCost}. `;
    } else {
        textToRead += `No pre verified treatment guidance is available in the local database. `;
    }
    
    speechUtterance = new SpeechSynthesisUtterance(textToRead);
    
    speechUtterance.onend = function() {
        resetSpeechButton();
    };
    
    speechUtterance.onerror = function() {
        resetSpeechButton();
    };
    
    isSpeaking = true;
    const ttsIcon = document.getElementById("ttsIcon");
    const ttsText = document.getElementById("ttsText");
    if (ttsIcon && ttsText) {
        ttsIcon.className = "fas fa-stop";
        ttsText.textContent = "Stop Listening";
    }
    
    window.speechSynthesis.speak(speechUtterance);
}

// ===============================
// PDF Export Feature
// ===============================

function generateReportPDF() {
    if (!currentResult) return;
    
    const { jsPDF } = window.jspdf;
    const doc = new jsPDF("p", "mm", "a4");
    
    let y = 15;
    
    // Header banner style
    doc.setFillColor(21, 128, 61); // dark green
    doc.rect(0, 0, 210, 25, "F");
    
    doc.setFont("Helvetica", "bold");
    doc.setFontSize(16);
    doc.setTextColor(255, 255, 255);
    doc.text("CROP DISEASE ANALYSIS & TREATMENT REPORT", 15, 16);
    
    y = 35;
    
    // Section 1: AI Findings
    doc.setFont("Helvetica", "bold");
    doc.setFontSize(12);
    doc.setTextColor(21, 128, 61);
    doc.text("1. GENERAL INFORMATION & AI ANALYSIS", 15, y);
    y += 4;
    doc.setDrawColor(220, 252, 231);
    doc.line(15, y, 195, y);
    y += 8;
    
    doc.setFont("Helvetica", "normal");
    doc.setFontSize(10);
    doc.setTextColor(31, 41, 55);
    
    doc.text(`Crop Name: ${currentResult.crop_name}`, 15, y);
    y += 6;
    doc.text(`Disease Name: ${currentResult.disease_name}`, 15, y);
    y += 6;
    doc.text(`Confidence Level: ${currentResult.confidence}`, 15, y);
    y += 6;
    doc.text(`Severity Level: ${currentResult.severity}`, 15, y);
    y += 6;
    
    // Sub-text wraps
    const fertText = doc.splitTextToSize(`Fertilizer Recommendation: ${currentResult.fertilizer_recommendation || "N/A"}`, 110);
    doc.text(fertText, 15, y);
    y += (fertText.length * 5) + 2;
    
    const waterText = doc.splitTextToSize(`Watering Advice: ${currentResult.watering_advice || "N/A"}`, 110);
    doc.text(waterText, 15, y);
    
    // Add crop image next to details
    const imgElement = document.getElementById("previewImage");
    if (imgElement && imgElement.src && imgElement.src.startsWith("data:image")) {
        try {
            doc.addImage(imgElement.src, "JPEG", 135, 41, 60, 50);
        } catch (err) {
            console.error("Failed to add image to PDF", err);
        }
    }
    
    y = 110;
    
    // Section 2: Symptoms & Causes
    doc.setFont("Helvetica", "bold");
    doc.setFontSize(12);
    doc.setTextColor(21, 128, 61);
    doc.text("2. SYMPTOMS & POSSIBLE CAUSES", 15, y);
    y += 4;
    doc.line(15, y, 195, y);
    y += 8;
    
    doc.setFont("Helvetica", "bold");
    doc.setFontSize(10);
    doc.setTextColor(220, 38, 38); // red-600
    doc.text("Symptoms:", 15, y);
    doc.setTextColor(202, 138, 4); // yellow-600
    doc.text("Possible Causes:", 110, y);
    y += 6;
    
    doc.setFont("Helvetica", "normal");
    doc.setTextColor(31, 41, 55);
    
    const symps = currentResult.symptoms || [];
    const causes = currentResult.possible_causes || [];
    
    let sympY = y;
    symps.forEach(s => {
        const lines = doc.splitTextToSize(`• ${s}`, 85);
        doc.text(lines, 15, sympY);
        sympY += (lines.length * 5);
    });
    
    let causeY = y;
    causes.forEach(c => {
        const lines = doc.splitTextToSize(`• ${c}`, 85);
        doc.text(lines, 110, causeY);
        causeY += (lines.length * 5);
    });
    
    y = Math.max(sympY, causeY) + 10;
    
    if (y > 230) {
        doc.addPage();
        y = 20;
    }
    
    // Section 3: Verified Treatment
    if (currentTreatment) {
        doc.setFont("Helvetica", "bold");
        doc.setFontSize(12);
        doc.setTextColor(21, 128, 61);
        doc.text("3. VERIFIED TREATMENT GUIDANCE", 15, y);
        y += 4;
        doc.line(15, y, 195, y);
        y += 8;
        
        doc.setFont("Helvetica", "bold");
        doc.setFontSize(10);
        doc.setTextColor(22, 101, 52); // green-800
        doc.text("Organic Treatment Plan:", 15, y);
        y += 6;
        
        doc.setFont("Helvetica", "normal");
        doc.setTextColor(31, 41, 55);
        (currentTreatment.organic_treatment || []).forEach((step, idx) => {
            const lines = doc.splitTextToSize(`Step ${idx + 1}: ${step}`, 180);
            doc.text(lines, 15, y);
            y += (lines.length * 5);
        });
        y += 2;
        
        const altText = doc.splitTextToSize(`Organic Alternatives: ${currentTreatment.alternative_organic_solutions || "N/A"}`, 180);
        doc.text(altText, 15, y);
        y += (altText.length * 5) + 6;
        
        if (y > 230) {
            doc.addPage();
            y = 20;
        }
        
        doc.setFont("Helvetica", "bold");
        doc.setTextColor(31, 41, 55);
        doc.text("Chemical & Medicine Treatment details:", 15, y);
        y += 6;
        
        doc.setFont("Helvetica", "normal");
        doc.text(`• Medicine Name: ${currentTreatment.chemical_treatment_name}`, 15, y);
        y += 5;
        doc.text(`• Active Ingredient: ${currentTreatment.active_ingredient}`, 15, y);
        y += 5;
        doc.text(`• Brand Examples: ${currentTreatment.example_brand_names}`, 15, y);
        y += 5;
        doc.text(`• Application Method: ${currentTreatment.application_method}`, 15, y);
        y += 8;
        
        if (y > 220) {
            doc.addPage();
            y = 20;
        }
        
        const landSize = document.getElementById("landSizeInput").value;
        const landUnit = document.getElementById("landUnitSelect").value;
        const totalMed = document.getElementById("mixingMedicine").textContent;
        const totalWater = document.getElementById("mixingWater").textContent;
        const tanksCount = document.getElementById("tanksCount").textContent;
        const perTankDosage = document.getElementById("perTankDosage").textContent;
        const tankCapacity = document.getElementById("sprayerCapacityInput").value;

        doc.setFont("Helvetica", "bold");
        doc.text("Mixing & Application Guidelines (Field Plan):", 15, y);
        y += 6;
        doc.setFont("Helvetica", "normal");
        doc.text(`• Land Area Coverage: ${landSize} ${landUnit.charAt(0).toUpperCase() + landUnit.slice(1)}`, 15, y);
        y += 5;
        doc.text(`• Total Field Water: ${totalWater} | Total Field Medicine: ${totalMed}`, 15, y);
        y += 5;
        doc.text(`• Spray Equipment: ${tanksCount} (Capacity: ${tankCapacity} L)`, 15, y);
        y += 5;
        doc.text(`• Per-Tank Mix Dosage: Mix ${perTankDosage} of medicine per tank run.`, 15, y);
        y += 8;
        
        doc.setFont("Helvetica", "bold");
        doc.text("Mixing Steps (Per Tank Run):", 15, y);
        y += 6;
        doc.setFont("Helvetica", "normal");
        
        const baseDosage = parseDosage(currentTreatment.mixing_quantity);
        (currentTreatment.mixing_steps || []).forEach((step, idx) => {
            let stepText = step;
            if (baseDosage) {
                const perTankVal = tankCapacity * (baseDosage.val / 15);
                const perTankValStr = (Math.round(perTankVal * 10) / 10) + " " + baseDosage.unit;
                const regex = new RegExp(`\\b${baseDosage.val}\\s*${baseDosage.unit}\\b`, 'gi');
                stepText = step.replace(regex, perTankValStr);
            }
            const lines = doc.splitTextToSize(`${idx + 1}. ${stepText}`, 175);
            doc.text(lines, 18, y);
            y += (lines.length * 5);
        });
        y += 6;
        
        if (y > 230) {
            doc.addPage();
            y = 20;
        }
        
        doc.setFont("Helvetica", "bold");
        doc.text("Spray Schedule & Safety:", 15, y);
        y += 6;
        doc.setFont("Helvetica", "normal");
        doc.text(`• Best Time: ${currentTreatment.spray_timing}`, 15, y);
        y += 5;
        doc.text(`• Repeat Interval: Repeat after ${currentTreatment.spray_interval} (Max ${currentTreatment.number_of_applications} applications)`, 15, y);
        y += 5;
        doc.text(`• PPE Required: ${currentTreatment.ppe_required}`, 15, y);
        y += 5;
        doc.text(`• Harvest Waiting Period: ${currentTreatment.waiting_period_before_harvest}`, 15, y);
        y += 8;
        
        if (y > 240) {
            doc.addPage();
            y = 20;
        }
        
        doc.setFont("Helvetica", "bold");
        doc.text("Expected Recovery Timeline:", 15, y);
        y += 6;
        doc.setFont("Helvetica", "normal");
        doc.text("• Day 1: Treatment Applied -> Day 3: Symptoms Reduce -> Day 7: Disease Controlled -> Day 14: Healthy New Growth", 15, y);
        y += 8;
        
        const costMed = document.getElementById("costMedicine").textContent;
        const costLab = document.getElementById("costLabour").textContent;
        const costTot = document.getElementById("costTotal").textContent;

        doc.setFont("Helvetica", "bold");
        doc.text("Estimated Cost breakdown (For Entire Field):", 15, y);
        y += 6;
        doc.setFont("Helvetica", "normal");
        doc.text(`• Medicine Cost: ${costMed} | Labour Cost: ${costLab} | Total Field Cost: ${costTot}`, 15, y);
        y += 10;
        
        doc.setFont("Helvetica", "italic");
        doc.setFontSize(8);
        doc.setTextColor(156, 163, 175);
        doc.text(`Source: ${currentTreatment.government_advisory_source} | Last Updated: ${currentTreatment.last_updated_date}`, 15, y);
        
    } else {
        doc.setFont("Helvetica", "bold");
        doc.setFontSize(12);
        doc.setTextColor(21, 128, 61);
        doc.text("3. VERIFIED TREATMENT GUIDANCE", 15, y);
        y += 4;
        doc.line(15, y, 195, y);
        y += 8;
        
        doc.setFont("Helvetica", "italic");
        doc.setFontSize(10);
        doc.setTextColor(107, 114, 128);
        doc.text("No verified treatment guidance is currently stored in the local database for this disease.", 15, y);
    }
    
    // Save report file
    const safeCrop = currentResult.crop_name.toLowerCase().replace(/\s+/g, '_');
    const safeDisease = currentResult.disease_name.toLowerCase().replace(/\s+/g, '_');
    doc.save(`report_${safeCrop}_${safeDisease}.pdf`);
}

// ===============================
// Sprayer & Land Area Calculator
// ===============================

function handleLandSizeChange() {
    const landSizeInput = document.getElementById("landSizeInput");
    let val = parseFloat(landSizeInput.value);
    if (isNaN(val) || val <= 0) return;
    updateSprayerCalculations();
}

function handleSprayerTypeChange() {
    const typeSelect = document.getElementById("sprayerTypeSelect");
    const capacityInput = document.getElementById("sprayerCapacityInput");
    
    if (typeSelect.value === "knapsack") {
        capacityInput.value = 15;
        capacityInput.readOnly = true;
        capacityInput.classList.add("cursor-not-allowed");
    } else if (typeSelect.value === "tractor") {
        capacityInput.value = 400;
        capacityInput.readOnly = true;
        capacityInput.classList.add("cursor-not-allowed");
    } else if (typeSelect.value === "custom") {
        capacityInput.readOnly = false;
        capacityInput.classList.remove("cursor-not-allowed");
    }
    updateSprayerCalculations();
}

function handleCapacityInput() {
    const capacityInput = document.getElementById("sprayerCapacityInput");
    let val = parseInt(capacityInput.value);
    if (isNaN(val) || val <= 0) return;
    if (val > 5000) {
        capacityInput.value = 5000;
    }
    updateSprayerCalculations();
}

function updateSprayerCalculations() {
    if (!currentTreatment) return;

    // 1. Read Inputs
    const landSizeInput = document.getElementById("landSizeInput");
    const landUnitSelect = document.getElementById("landUnitSelect");
    const capacityInput = document.getElementById("sprayerCapacityInput");

    let landSize = parseFloat(landSizeInput.value) || 1.0;
    let landUnit = landUnitSelect.value || "acres";
    let tankCapacity = parseInt(capacityInput.value) || 15;

    // 2. Estimate total water volume needed for field
    // 200 L per acre / 500 L per hectare
    let waterPerUnit = (landUnit === "acres") ? 200 : 500;
    let totalWaterVolume = Math.round(landSize * waterPerUnit);

    // 3. Calculate sprayer runs (number of tanks) needed
    let totalTanks = Math.ceil(totalWaterVolume / tankCapacity);

    // 4. Parse base concentration ratio from database
    // Base database calibration is ALWAYS for 15 Litres of water
    const baseDosage = parseDosage(currentTreatment.mixing_quantity);
    
    let totalMedicineStr = "N/A";
    let perTankDosageStr = "N/A";

    if (baseDosage) {
        // Concentration per Liter = base_value / 15
        const concentrationPerLiter = baseDosage.val / 15;

        // Total Field Medicine
        const totalMedVal = totalWaterVolume * concentrationPerLiter;
        // Format nicely
        const totalMedFormatted = Math.round(totalMedVal * 10) / 10;
        totalMedicineStr = `${totalMedFormatted} ${baseDosage.unit}`;

        // Per-Tank Mix Dosage
        const perTankVal = tankCapacity * concentrationPerLiter;
        const perTankFormatted = Math.round(perTankVal * 10) / 10;
        perTankDosageStr = `${perTankFormatted} ${baseDosage.unit}`;
    }

    // Update Output Cards
    document.getElementById("mixingMedicine").textContent = totalMedicineStr;
    document.getElementById("mixingWater").textContent = `${totalWaterVolume} Litres`;
    document.getElementById("tanksCount").textContent = `${totalTanks} Runs (${tankCapacity}L per Tank)`;
    document.getElementById("perTankDosage").textContent = perTankDosageStr;

    // 5. Update Mixing Steps Text
    // We update mixing steps to tell the user the per-tank mixing instructions
    const mixingSteps = document.getElementById("mixingSteps");
    mixingSteps.innerHTML = "";
    if (currentTreatment.mixing_steps && currentTreatment.mixing_steps.length > 0) {
        currentTreatment.mixing_steps.forEach((step, idx) => {
            let stepText = step;
            if (baseDosage) {
                // Scale value for a single tank run
                const perTankVal = tankCapacity * (baseDosage.val / 15);
                const perTankValStr = (Math.round(perTankVal * 10) / 10) + " " + baseDosage.unit;
                
                // Match "30g" or "30 g" or "15ml" or "15 ml"
                const regex = new RegExp(`\\b${baseDosage.val}\\s*${baseDosage.unit}\\b`, 'gi');
                stepText = step.replace(regex, perTankValStr);
            }
            const stepDiv = document.createElement("div");
            stepDiv.className = "flex items-start space-x-3 mb-2";
            stepDiv.innerHTML = `
                <span class="text-xs font-bold text-green-600 shrink-0">${idx + 1}.</span>
                <p class="text-xs text-gray-600 leading-relaxed">${stepText}</p>
            `;
            mixingSteps.appendChild(stepDiv);
        });
    }

    // 6. Scale Costs based on total field volume (Total water / 15)
    const costMultiplier = totalWaterVolume / 15;
    const scaledMedCost = Math.round(currentTreatment.cost_estimate_medicine * costMultiplier);
    const scaledLabCost = Math.round(currentTreatment.cost_estimate_labour * costMultiplier);
    const scaledTotalCost = scaledMedCost + scaledLabCost;

    document.getElementById("costMedicine").textContent = `₹${scaledMedCost}`;
    document.getElementById("costLabour").textContent = `₹${scaledLabCost}`;
    document.getElementById("costTotal").textContent = `₹${scaledTotalCost}`;
}

function parseDosage(dosageStr) {
    if (!dosageStr) return null;
    const match = dosageStr.match(/^(\d+(?:\.\d+)?)\s*(g|ml|kg|l)\b/i);
    if (match) {
        return { val: parseFloat(match[1]), unit: match[2] };
    }
    return null;
}