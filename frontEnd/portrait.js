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
    
    // Thêm dòng báo đang tải để người dùng biết máy đang chấm
    result.innerHTML = `<p style="color: #007bff; font-weight: bold;">⌛ Đang phân tích và chấm điểm...</p>`;

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
            commentText = "🌟 Rất tốt!, chúc mừng em bảo bối à!";
        } else if (data.score >= 7) {
            commentText = "👍 Tốt nhưng còn thiếu chút nha cục dàng";
        } else if (data.score >= 5) {
            commentText = "🙂 Ổn nhưng em nên cải thiện hơn nhé nha cục dàng";
        } else {
            commentText = "😅 Cần cố gắng nhiều hơn nha em huhu";
        }

        let scoreImg = "";
        if (data.score >= 8) {
            scoreImg = "../frontEnd/ảnhMeMe/perfectMeMe.jpg";
        } else if (data.score >= 5 && data.score < 8) {
            scoreImg = "../frontEnd/ảnhMeMe/itsAlright.jpg";
        } else if (data.score < 5 && data.score >= 3) {
            scoreImg = "../frontEnd/ảnhMeMe/pray.jpg";
        } else {
            scoreImg = "../frontEnd/ảnhMeMe/blackCry.jpg";
        }

        let detectedHTML = "";
        let missingHTML = "";

        const detected = data.detected || [];
        const missing = data.missing || [];

        if (detected.length > 0) {
            detectedHTML = `<p>✅ <b>Phát hiện có:</b> ${detected.join(", ")}</p>`;
        }

        if (missing.length > 0) {
            missingHTML = `<p id="missing" style="color: red;">❌ <b>Thiếu mất rồi:</b> ${missing.join(", ")}</p>`;
        }

        // Xử lý hiển thị Luật mềm & Ảnh Boxed an toàn
        let loaiTranhText = classifyData.type === "ChanDung" ? "🧑 Chân dung" : "🌄 Phong cảnh";
        let boxedImageHTML = data.boxed_image ? `<img src="http://127.0.0.1:5000${data.boxed_image}" style="max-width: 100%; border: 2px solid #007bff; border-radius: 8px; margin: 10px 0;">` : "";
        
        let luatMemHTML = "";
        
        // Sửa lỗi ghép mảng (join) an toàn cho tất cả các field
        let nhanXetBoCuc = data.nhan_xet_bo_cuc || data.danh_gia_bo_cuc;
        if (nhanXetBoCuc && Array.isArray(nhanXetBoCuc)) luatMemHTML += `<p>📐 <b>Bố cục:</b> ${nhanXetBoCuc.join(" ")}</p>`;
        
        if (data.nhan_xet_ty_le && Array.isArray(data.nhan_xet_ty_le) && data.nhan_xet_ty_le.length > 0) {
            luatMemHTML += `<p>👤 <b>Tỷ lệ mặt:</b> ${data.nhan_xet_ty_le.join("<br>")}</p>`;
        }
        
        if (data.nhan_xet_mau_sac) {
            luatMemHTML += `<p>🎨 <b>Màu sắc:</b> ${data.nhan_xet_mau_sac}</p>`;
        }
        
        if (data.nhan_xet_nghe_thuat && Array.isArray(data.nhan_xet_nghe_thuat) && data.nhan_xet_nghe_thuat.length > 0) {
            luatMemHTML += `<p>🖼️ <b>Nghệ thuật:</b> ${data.nhan_xet_nghe_thuat.join(" ")}</p>`;
        }
        
        if (data.loi_khuyen_giao_vien && Array.isArray(data.loi_khuyen_giao_vien) && data.loi_khuyen_giao_vien.length > 0) {
            luatMemHTML += `<p style="background: #eef2ff; padding: 12px; border-left: 5px solid #0056b3; border-radius: 4px; margin-top:15px; font-style: italic;">💡 <b>Lời khuyên từ giáo viên:</b><br>${data.loi_khuyen_giao_vien.join("<br>")}</p>`;
        }

        result.innerHTML = `
            <div style="background: #f9f9f9; padding: 15px; border-radius: 8px; border: 1px solid #ddd; margin-bottom: 15px;">
                <p style="margin-top:0;"><b>🏷️ AI nhận diện:</b> <span style="font-weight:bold; color:#0056b3;">${loaiTranhText}</span></p>
                <h3 style="margin-bottom:0; color: #333;">🎯 Điểm số: <span style="font-size: 1.5em; color: #ff5722;">${data.score}/10</span></h3>
            </div>
            
            ${boxedImageHTML}
            
            <div style="text-align: left; margin-bottom: 15px; line-height: 1.6;">
                ${detectedHTML}
                ${missingHTML}
                <hr style="border: 0; border-top: 1px solid #eee; margin: 15px 0;">
                ${luatMemHTML}
            </div>
            
            <p style="color: #ff5722; font-size: 1.1em; text-align: center;"><b>${commentText}</b></p>
            <img src="${scoreImg}" class="score-img" style="max-width: 200px; display: block; margin: 0 auto; border-radius: 10px;">
        `;

    } catch (error) {
        console.error("Lỗi:", error);
        result.innerHTML = `<p style="color: red; font-weight: bold; padding: 10px; background: #ffe6e6; border-radius: 5px;">❌ Lỗi: ${error.message} <br><small>(Bạn nhớ bật file Python chạy Server lên nhé!)</small></p>`;
    }
};