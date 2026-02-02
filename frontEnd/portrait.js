let artType = "portrait";


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
    const commentEl = document.getElementById("comment");

    if (!imageFile) {
        alert("Chưa chọn ảnh");
        return;
    }

    preview.src = URL.createObjectURL(imageFile);
    preview.style.display = "block";

    const formData = new FormData();
    formData.append("image", imageFile);

    const url =
        artType === "portrait"
            ? "http://127.0.0.1:5000/predict"
            : "http://127.0.0.1:5000/predict_scenery";

    fetch(url, {
        method: "POST",
        body: formData
    })
        .then(res => res.json())
        .then(data => {
            let commentText = "";
            let commentImg = "";
            if (data.score >= 9) {
                commentText = "🌟 Rất tốt!";
                commentImg = "C:\Users\dev\AnhEmToiDanhLe\frontEnd\ảnhMeMe\perfectMeMe.jpg"
            }
            else if (data.score >= 7) {
                commentText = "👍 Tốt nhưng còn thiếu chút";
                commentImg = "C:\Users\dev\AnhEmToiDanhLe\frontEnd\ảnhMeMe\itsAlright.jpg"


            } else if (data.score >= 5) {
                commentText = "🙂 Ổn, nên cải thiện thêm";
                commentImg = "C:\Users\dev\AnhEmToiDanhLe\frontEnd\ảnhMeMe\pray.jpg"


            } else {
                commentText = "😅 Cần cố gắng nhiều hơn";
                commentImg = "C:\Users\dev\AnhEmToiDanhLe\frontEnd\ảnhMeMe\blackCry.jpg"



            }
            result.innerHTML = `
                <p><b>🎯 Score:</b> ${data.score}</p>
                <p>❌ Missing: ${(data.missing || []).join(", ")}</p>
                <p><b>${commentText}</b></p>
            `;
        })
        .catch(() => {
            result.innerText = "❌ Lỗi gọi API";
        });
};
