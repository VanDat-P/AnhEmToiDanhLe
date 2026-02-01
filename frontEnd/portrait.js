document.getElementById("submit").onclick = () => {
    const imageFile = document.getElementById("image").files[0];
    // const imageFile = document.getElementById("img_input").files[0];
    const result = document.getElementById("result");

    if (!imageFile) {
        alert("Chưa chọn ảnh");
        return;
    }

    const formData = new FormData();
    formData.append("image", imageFile);

    fetch("http://127.0.0.1:5000/predict", {
        method: "POST",
        body: formData
    })
        .then(res => res.json())
        .then(data => {
            result.innerHTML = `
                <p><b>🎯 Điểm:</b> ${data.score}</p>
                <p>✅ có: ${data.detected.join(", ")}</p>
                <p>❌ Thiếu: ${data.missing.join(", ")}</p>
            `;
        })
        .catch(err => {
            console.error(err);
            result.innerText = "❌ Lỗi gọi API";
        });
};
