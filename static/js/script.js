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

uploadForm.addEventListener("submit", async function(e){

    e.preventDefault();

    if(imageInput.files.length===0){

        alert("Please select an image.");

        return;

    }

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

        displayResult(data.result);

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

function displayResult(result){

    resultSection.classList.remove("hidden");

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