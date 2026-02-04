let artType = "portrait";

document.getElementById("btn-portrait").onclick = () => {
    chooseType("portrait");
};

document.getElementById("btn-scenery").onclick = () => {
    chooseType("scenery");
};

document.getElementById("back").onclick = () => {
    // reset loại tranh
    artType = "portrait";

    // hiện card chọn loại
    document.getElementById("select-type-card").style.display = "block";
    document.getElementById("grading-card").style.display = "none";

    // reset input & kết quả
    document.getElementById("image").value = "";
    document.getElementById("preview").style.display = "none";

    document.getElementById("result").innerHTML = `
        <span class="placeholder-text">
            Kết quả của bạn sẽ là gì đây nào?...
        </span>
    `;
};

function chooseType(type) {
    artType = type;

    document.getElementById("select-type-card").style.display = "none";
    document.getElementById("grading-card").style.display = "block";

    document.getElementById("title").innerText =
        type === "portrait"
            ? "Chấm điểm tranh chân dung"
            : "Chấm điểm tranh phong cảnh";
}

document.getElementById("submit").onclick = () => {
    const imageFile = document.getElementById("image").files[0];
    const result = document.getElementById("result");
    const preview = document.getElementById("preview");
   
    if (!imageFile) {
        alert("Chưa chọn ảnh");
        return;
    }

    preview.src = URL.createObjectURL(imageFile);
    preview.style.display = "block";

    const formData = new FormData();
    formData.append("image", imageFile);

    let url = "http://127.0.0.1:5000/predict"

    if (artType === "scenery") {
        url = "http://127.0.0.1:5000/predict_scenery";
    }

    fetch(url, {
        method: "POST",
        body: formData
    })
        .then(res => res.json())
        .then(data => {
            let commentText = "";
           
            if (data.score >= 9) {
                commentText = "🌟 Rất tốt!";

            }
            else if (data.score >= 7) {
                commentText = "👍 Tốt nhưng còn thiếu chút";



            } else if (data.score >= 5) {
                commentText = "🙂 Ổn, nên cải thiện thêm";



            } else {
                commentText = "😅 Cần cố gắng nhiều hơn";



            }
            let scoreImg = "";

            if (data.score >= 8) {
            scoreImg = "../frontEnd/ảnhMeMe/perfectMeMe.jpg";
            } else if (data.score >5 && data.score <8) {
            scoreImg = "../frontEnd/ảnhMeMe/itsAlright.jpg";
            } else if (data.score <5 && data.score >3) {
            scoreImg = "../frontEnd/ảnhMeMe/pray.jpg";
            } else {
            scoreImg = "../frontEnd/ảnhMeMe/blackCry.jpg";
            }
             
            let detectedHTML = "";
            let missingHTML = "";

            const detected = data.detected || [];
            const missing = data.missing || [];
            let loaiTranh = artType === "portrait" ? "chân dung" : "phong cảnh";
            if (detected.length > 0) {
                detectedHTML = `<p>Có: ${detected.join(", ")}</p>`;
            }
            if (detected.length == 0) {
                 missingHTML = `<p id="missing">này mà là tranh ${loaiTranh} hả ?</p>`;
                //  missingHTML = `<p id="missing">❌ Missing: ${missing.join(", ")}</p>`;
                
            }
            
            if (detected.length > 0 && missing.length > 0) {
                missingHTML = `<p id="missing">❌ Missing: ${missing.join(", ")}</p>`;
            }
            if(missing.length == 0)  missingHTML = `<p id="missing"></p>`;

            result.innerHTML = `
                <p><b>🎯 Score:</b> ${data.score}</p>
                ${detectedHTML}
                ${missingHTML}
                <p><b>${commentText}</b></p>
                <img src="${scoreImg}" class="score-img">

            `;
        })
        .catch(() => {
            result.innerText = "❌ Lỗi gọi API";
        });
}; 