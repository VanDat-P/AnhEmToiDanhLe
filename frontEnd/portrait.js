document.getElementById("submit").onclick = () => {
    const imageFile = document.getElementById("image").files[0];
    const result = document.getElementById("result");
    const preview = document.getElementById("preview");
    const commentEl = document.getElementById("comment");


    if (!imageFile) {
        alert("Chưa chọn ảnh");
        return;
    }

    preview.src = URL.createObjectURL(imageFile);
    preview.style.display = "block";

    const formData = new FormData();
    formData.append("image", imageFile);

    fetch("http://127.0.0.1:5000/predict", {
        method: "POST",
        body: formData
    })
        .then(res => res.json())
        .then(data => {

            let commentText = "";
            // let imgSrc = "";

            if (data.score >= 9) {
                commentText = "quite good";

            } else if (data.score >= 7) {
                commentText = "good but not enough";
            } else if (data.score >= 5) {
                commentText = "🙂 Not bad! Try to improve the facial structure.";
            } else {
                commentText = "what a silly guy ?";
            }
            commentEl.innerText = commentText;


            result.innerHTML = `
            <p><b>🎯 Score:</b> ${data.score}</p>
            <p>❌ Missing: ${data.missing.join(", ")}</p>
            <p><b> ${commentText}</b></p>
        `;
        })
        .catch(err => {
            console.error(err);
            result.innerText = "❌ Lỗi gọi API";
        });
};
