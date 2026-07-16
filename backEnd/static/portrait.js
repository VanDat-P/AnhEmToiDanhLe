document.getElementById("submit").onclick = async () => {
    const penalty = localStorage.getItem("penalty") || 1;
    const imageFile = document.getElementById("image").files[0];
    const result = document.getElementById("result");
    const preview = document.getElementById("preview");
   
    if (!imageFile) {
        alert("Chưa chọn ảnh");
        return; 
    }

    preview.src = URL.createObjectURL(imageFile);
    preview.style.display = "block";
    document.getElementById("yourImageTitle").style.display = "block";
    
    // Hiển thị loading
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
        scoreFormData.append("image", imageFile);
        scoreFormData.append("penalty", penalty);

        // Chọn URL dựa trên kết quả phân loại
        let url;
        if (classifyData.type === "ChanDung") {
            url = "http://127.0.0.1:5000/predict";
        } else if (classifyData.type === "PhongCanh") {
            url = "http://127.0.0.1:5000/predict_scenery";
        } else {
            result.innerHTML = `
                <div style="background: #e3f2fd; padding: 25px; border-radius: 20px; border: 3px solid #90caf9; text-align: center; box-shadow: 0 4px 8px rgba(0,0,0,0.1);">
                    <div style="font-size: 4em; margin: 10px 0;">🎨</div>
                    <p style="color: #42a5f5; font-size: 1.3em; margin: 15px 0;">
                        Có vẻ như em đang cố vẽ một bức tranh thật đặc biệt! 
                    </p>
                    <p style="color: #66bb6a; font-size: 1.2em; background: #c8e6c9; padding: 15px; border-radius: 15px; margin: 15px 0;">
                        🌟 Lần tới, em thử vẽ thêm chi tiết cho khuôn mặt <br>
                        hoặc vẽ nhà, cây, ông mặt trời để đạt điểm cao hơn nhé!
                    </p>
                    <div style="margin-top: 20px;">
                        <span style="font-size: 2em;"></span>
                        <span style="font-size: 2em;"></span>
                        <span style="font-size: 2em;"></span>
                    </div>
                    <p style="color: #ffa726; font-style: italic; margin-top: 20px;">Bức tranh của em rất sáng tạo! Cố gắng thêm chút nữa nhé! 💪</p>
                </div>
            `;
            return;
        }
        
        // Gọi API chấm điểm
        const scoreRes = await fetch(url, {
            method: "POST",
            body: scoreFormData
        });

        if (!scoreRes.ok) {
            const err = await scoreRes.json();
            throw new Error(err.error || "Lỗi chấm điểm");
        }

        const data = await scoreRes.json();
        const breakdown = data.score_breakdown;

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

        // Fix đường dẫn ảnh meme
        let scoreImg = "";
        if (data.score >= 8) {
            scoreImg = "ảnhMeMe/perfectMeMe.jpg";
        } else if (data.score >= 5) {
            scoreImg = "ảnhMeMe/itsAlright.jpg";
        } else if (data.score >= 3) {
            scoreImg = "ảnhMeMe/pray.jpg";
        } else {
            scoreImg = "ảnhMeMe/blackCry.jpg";
        }

        // Xử lý detected/missing
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

        // === THÊM HIỂN THỊ NOUNS VÀ VERBS TỪ SETTINGS ===
        let nounsSettingsHTML = "";
        let verbsSettingsHTML = "";
        let bonusHTML = "";
        
        if (data.nouns_from_settings && data.nouns_from_settings.length > 0) {
            nounsSettingsHTML = `<p>📚 <b>Từ khóa vật thể (từ mô tả):</b> ${data.nouns_from_settings.join(", ")}</p>`;
        }
        
        if (data.verbs_from_settings && data.verbs_from_settings.length > 0) {
            verbsSettingsHTML = `<p>🎨 <b>Từ khóa kỹ thuật (từ mô tả):</b> ${data.verbs_from_settings.join(", ")}</p>`;
        }
        
        if (data.bonus_from_nouns > 0 || data.bonus_from_verbs > 0) {
            bonusHTML = `<p style="color: #10b981;">✨ <b>Điểm thưởng từ mô tả:</b> +${(data.bonus_from_nouns || 0) + (data.bonus_from_verbs || 0)} điểm</p>`;
        }

        // Xử lý hiển thị
        let loaiTranhText = classifyData.type === "ChanDung" ? " Chân dung" : " Phong cảnh";
        let boxedImageHTML = "";
        let breakdownHTML = "";
        if (breakdown) {
                let detailHTML = "";

                breakdown.details.forEach(item => {

                    detailHTML += `
                        <div class="criteria-card">

                            <div class="criteria-header">
                                <h3>${item.title}</h3>
                                <span class="criteria-score">
                                    ${item.score}/${item.max}
                                </span>
                            </div>

                            <p class="criteria-desc">
                                ${item.description || ""}
                            </p>

                            <p>
                                <b>Phương pháp đánh giá:</b>
                                ${item.formula || "-"}
                            </p>

                            ${
                                item.detected ?
                                `<p><b>Đã phát hiện:</b> ${item.detected.join(", ")}</p>`
                                :""
                            }

                            ${
                                item.missing ?
                                `<p style="color:red">
                                    <b>Thiếu:</b>
                                    ${item.missing.join(", ")}
                                </p>`
                                :""
                            }

                            ${
                                item.result ?
                                `<ul>
                                    ${item.result.map(r=>`<li>${r}</li>`).join("")}
                                </ul>`
                                :""
                            }

                        </div>
                        `;

                });
               
                    breakdownHTML = `
                    <div class="score-breakdown">

                        <button id="showBreakdown" class="breakdown-btn">
                            📊 Xem chi tiết cách chấm điểm
                        </button>

                        <div id="breakdownBox" style="display:none;">

                            <h2>📋 Báo cáo chấm điểm</h2>
                            <h3>📑 Chi tiết từng tiêu chí</h3>

                            ${detailHTML}
                            <div class="score-section">

                                <h3> Điểm từng tiêu chí</h3>

                                <table class="score-table">
                                    <thead>
                                        <tr>
                                            <th>Tiêu chí</th>
                                            <th>Điểm</th>
                                            <th>Nhận xét</th>
                                        </tr>
                                    </thead>

                                    <tbody>

                                        ${breakdown.details.map(item=>{

                                            let note="";

                                            if(item.score >= item.max*0.9)
                                                note="Rất tốt";
                                            else if(item.score >= item.max*0.7)
                                                note="Tốt";
                                            else if(item.score >= item.max*0.5)
                                                note="Đạt";
                                            else
                                                note="Cần cải thiện";

                                            return `
                                            <tr>
                                                <td>${item.title}</td>
                                                <td>${item.score}/${item.max}</td>
                                                <td>${note}</td>
                                            </tr>
                                            `;

                                        }).join("")}

                                    </tbody>

                                </table>

                            </div>

                            <div class="score-section">

                                <h3> Điểm cộng</h3>

                                ${
                                    breakdown.bonus.length>0 ?
                                    `<ul>
                                        ${breakdown.bonus.map(item=>`
                                            <li><b>+${item.point}</b> : ${item.reason}</li>
                                        `).join("")}
                                    </ul>`
                                    :
                                    `<p>Không có điểm cộng.</p>`
                                }

                            </div>

                            <div class="score-section">

                                <h3> Điểm trừ</h3>

                                ${
                                    breakdown.penalty.length>0 ?
                                    `<ul>
                                        ${breakdown.penalty.map(item=>`
                                            <li><b>-${item.point}</b> : ${item.reason}</li>
                                        `).join("")}
                                    </ul>`
                                    :
                                    `<p>Không có điểm trừ.</p>`
                                }

                            </div>

                            <div class="score-section">

                                <h3> Công thức tính điểm</h3>

                                <table class="formula-table">

                                    <tr>
                                        <td>Điểm cơ bản</td>
                                        <td>${breakdown.formula.base}</td>
                                    </tr>

                                    <tr>
                                        <td>Điểm cộng</td>
                                        <td style="color:green;">
                                            +${breakdown.formula.bonus}
                                        </td>
                                    </tr>

                                    <tr>
                                        <td>Điểm trừ</td>
                                        <td style="color:red;">
                                            -${breakdown.formula.penalty}
                                        </td>
                                    </tr>

                                    <tr>
                                        <td>Mức phạt độ khó</td>
                                        <td style="color:#ff9800;">
                                            -${breakdown.formula.difficulty}
                                        </td>
                                    </tr>

                                </table>

                                <div class="final-score">

                                     Điểm cuối cùng

                                    <div class="score-number">

                                        ${breakdown.formula.final}/10

                                    </div>

                                </div>

                            </div>

                        </div>

                    </div>
                    `;
        }
        if (data.boxed_image) {
            boxedImageHTML = `
                <button id="showDetected" style="
                    background:#007bff;
                    color:white;
                    border:none;
                    padding:8px 15px;
                    border-radius:5px;
                    cursor:pointer;
                    margin-bottom:10px;">
                     👀 Xem ảnh AI phát hiện
                </button>
                <div id="detectedBox" style="display:none;">
                    <img src="http://127.0.0.1:5000${data.boxed_image}" 
                    style="max-width:100%; border:2px solid #007bff; border-radius:8px; margin:10px 0;">
                </div>
            `;
        }

        // Xử lý nhận xét
        let luatMemHTML = "";
        
        if (data.nhan_xet_bo_cuc && Array.isArray(data.nhan_xet_bo_cuc)) {
            luatMemHTML += `<p>📐 <b>Bố cục:</b> ${data.nhan_xet_bo_cuc.join(" ")}</p>`;
        }
        
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
                ${bonusHTML}
            </div>
            
            ${boxedImageHTML}
            
            <div style="text-align: left; margin-bottom: 15px; line-height: 1.6;">
                <div id="detectInfo" style="display:none;">
                    ${detectedHTML}
                    ${missingHTML}
                    ${nounsSettingsHTML}
                    ${verbsSettingsHTML}
                    <hr style="border: 0; border-top: 1px solid #eee; margin: 15px 0;">
                    <p><b>📊 Tổng số vật cần có:</b> ${data.total_required || 0}</p>
                    <p><b>✅ Đã có:</b> ${detected.length}</p>
                    <p><b>❌ Thiếu:</b> ${missing.length}</p>
                </div>
                <hr style="border: 0; border-top: 1px solid #eee; margin: 15px 0;">
                ${luatMemHTML}
                ${breakdownHTML} 
            </div>
            
            <p style="color: #ff5722; font-size: 1.1em; text-align: center;"><b>${commentText}</b></p>
            <img src="${scoreImg}" class="score-img" style="max-width: 200px; display: block; margin: 0 auto; border-radius: 10px;" onerror="this.style.display='none'">
        `;

        
        // Đổi layout
        document.getElementById("content").classList.add("horizontal-layout");
        document.querySelector(".main-card").classList.add("wide");
        document.getElementById("resetBtn").style.display = "block";
        document.getElementById("submit").style.display = "none";
        document.querySelector(".upload-box").style.display = "none";

        // Xử lý nút xem ảnh phát hiện
        const btn = document.getElementById("showDetected");
        const btnBreak = document.getElementById("showBreakdown");

        if(btnBreak){

            btnBreak.onclick=()=>{

                const box=document.getElementById("breakdownBox");

                if(box.style.display=="none"){

                    box.style.display="block";

                    btnBreak.innerText="Ẩn cách chấm";

                }else{

                    box.style.display="none";

                    btnBreak.innerText="📊 Cách chấm điểm";

                }

            }

        }
        if (btn) {
            btn.onclick = () => {
                const box = document.getElementById("detectedBox");
                const info = document.getElementById("detectInfo");
                if (box.style.display === "none") {
                    box.style.display = "block";
                    info.style.display = "block";
                    btn.innerText = "🙈 Ẩn ảnh AI phát hiện";
                } else {
                    box.style.display = "none";
                    info.style.display = "none";
                    btn.innerText = "👀 Xem ảnh AI phát hiện";
                }
            };
        }
    } catch (error) {
        console.error("Lỗi:", error);
        result.innerHTML = `<p style="color: red; font-weight: bold; padding: 10px; background: #ffe6e6; border-radius: 5px;">❌ Lỗi: ${error.message} <br><small>(Bạn nhớ bật file Python chạy Server lên nhé!)</small></p>`;
    }
};

document.getElementById("resetBtn").onclick = () => {
    document.getElementById("image").value = "";
    document.getElementById("preview").style.display = "none";
    document.getElementById("yourImageTitle").style.display = "none";
    document.getElementById("resetBtn").style.display = "none";
    document.getElementById("result").innerHTML =
        `<span class="placeholder-text">
            Kết quả của bạn sẽ là gì đây nào?...
         </span>`;
    document.getElementById("content").classList.remove("horizontal-layout");
    document.querySelector(".main-card").classList.remove("wide");
    document.getElementById("submit").style.display = "block";
    document.querySelector(".upload-box").style.display = "block";
};