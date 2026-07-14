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

imageInput.addEventListener("click", (e) => {
    e.stopPropagation();
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

        if (data.filename) {
            data.result.filename = data.filename;
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
            document.getElementById("govAdvisory").textContent = "";
            document.getElementById("lastUpdated").textContent = "";
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

async function generateReportPDF() {
    if (!currentResult) return;
    
    const pdfBtn = document.getElementById("pdfBtn");
    const originalContent = pdfBtn.innerHTML;
    pdfBtn.disabled = true;
    pdfBtn.innerHTML = `<i class="fas fa-spinner fa-spin"></i> <span>Generating PDF...</span>`;

    // Extract sprayer calculator variables if available
    let calculatorMetrics = null;
    const landSizeInput = document.getElementById("landSizeInput");
    if (landSizeInput) {
        calculatorMetrics = {
            land_size: landSizeInput.value,
            land_unit: document.getElementById("landUnitSelect").value,
            total_medicine: document.getElementById("mixingMedicine").textContent,
            total_water: document.getElementById("mixingWater").textContent,
            tanks_count: document.getElementById("tanksCount").textContent,
            per_tank_dosage: document.getElementById("perTankDosage").textContent,
            tank_capacity: document.getElementById("sprayerCapacityInput").value,
            cost_medicine: document.getElementById("costMedicine").textContent,
            cost_labour: document.getElementById("costLabour").textContent,
            cost_total: document.getElementById("costTotal").textContent
        };
    }

    const payload = {
        crop_name: currentResult.crop_name,
        disease_name: currentResult.disease_name,
        confidence: currentResult.confidence,
        severity: currentResult.severity,
        symptoms: currentResult.symptoms,
        possible_causes: currentResult.possible_causes,
        prevention: currentResult.prevention,
        treatment: currentResult.treatment,
        fertilizer_recommendation: currentResult.fertilizer_recommendation,
        watering_advice: currentResult.watering_advice,
        additional_notes: currentResult.additional_notes,
        filename: currentResult.filename || "",
        treatment_guidance: currentTreatment || null,
        calculator_metrics: calculatorMetrics
    };

    try {
        const response = await fetch("/generate-pdf", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            throw new Error("Failed to generate PDF");
        }

        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.style.display = "none";
        a.href = url;
        
        const cleanCrop = (currentResult.crop_name || "Crop").replace(/\s+/g, "");
        const cleanDisease = (currentResult.disease_name || "Disease").replace(/\s+/g, "");
        const dateStr = new Date().toISOString().slice(0, 10);
        a.download = `${cleanCrop}_${cleanDisease}_${dateStr}.pdf`;
        
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
    } catch (error) {
        alert("Error generating PDF: " + error.message);
    } finally {
        pdfBtn.disabled = false;
        pdfBtn.innerHTML = originalContent;
    }
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
