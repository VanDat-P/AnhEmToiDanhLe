document.getElementById("submit").onclick = async () => {
    const imageFile = document.getElementById("image").files[0];
    const result = document.getElementById("result");
    const preview = document.getElementById("preview");
   
    if (!imageFile) {
        alert("Chưa chọn ảnh");
        return;
    }

    preview.src = URL.createObjectURL(imageFile);
    preview.style.display = "block";

    try {
        // Tạo FormData cho phân loại
        const classifyFormData = new FormData();
        classifyFormData.append("image", imageFile);

        // Gọi API phân loại
        const classifyRes = await fetch("http://127.0.0.1:5000/classify", {
            method: "POST",
            body: classifyFormData
        });

        if (!classifyRes.ok) {
            const err = await classifyRes.json();
            throw new Error(err.error || "Lỗi classify");
        }

        const classifyData = await classifyRes.json();
        
        // Tạo FormData MỚI cho chấm điểm
        const scoreFormData = new FormData();
        scoreFormData.append("image", imageFile); // Thêm file lại từ đầu

        // Chọn URL dựa trên kết quả phân loại
        let url = classifyData.type === "ChanDung"
            ? "http://127.0.0.1:5000/predict"
            : "http://127.0.0.1:5000/predict_scenery";

        // Gọi API chấm điểm
        const scoreRes = await fetch(url, {
            method: "POST",
            body: scoreFormData
        });

        const data = await scoreRes.json();

        // Hiển thị kết quả
        let commentText = "";
        if (data.score >= 9) {
            commentText = "🌟 Rất tốt!";
        } else if (data.score >= 7) {
            commentText = "👍 Tốt nhưng còn thiếu chút";
        } else if (data.score >= 5) {
            commentText = "🙂 Ổn, nên cải thiện thêm";
        } else {
            commentText = "😅 Cần cố gắng nhiều hơn";
        }

        let scoreImg = "";
        if (data.score >= 8) {
            scoreImg = "../static/images/meme/perfectMeMe.jpg";
        } else if (data.score > 5 && data.score < 8) {
            scoreImg = "../static/images/meme/itsAlright.jpg";
        } else if (data.score < 5 && data.score > 3) {
            scoreImg = "../static/images/meme/pray.jpg";
        } else {
            scoreImg = "../static/images/meme/blackCry.jpg";
        }

        let detectedHTML = "";
        let missingHTML = "";

        const detected = data.detected || [];
        const missing = data.missing || [];

        if (detected.length > 0) {
            detectedHTML = `<p>Có: ${detected.join(", ")}</p>`;
        }

        if (detected.length == 0 || missing.length > 0) {
            missingHTML = `<p id="missing">❌ Missing: ${missing.join(", ")}</p>`;
        }

        result.innerHTML = `
            <p><b>🎯 Score:</b> ${data.score}</p>
            ${detectedHTML}
            ${missingHTML}
            <p><b>${commentText}</b></p>
            <img src="${scoreImg}" class="score-img">
        `;

    } catch (error) {
        console.error("Lỗi:", error);
        result.innerText = "❌ Lỗi: " + error.message;
    }
};