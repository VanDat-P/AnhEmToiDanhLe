const slider = document.getElementById("penaltySlider");

slider.addEventListener("change", () => {

    fetch("/adjustment", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            penalty: slider.value
        })
    });
    console.log('Person A here.')

});