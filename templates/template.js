function openSquareAuth(url) {
    const width = 600;
    const height = 700;

    // Center the popup on screen
    const left = (window.innerWidth - width) / 2;
    const top = (window.innerHeight - height) / 2;

    window.open(
        url,
        "SquareAuthPopup",
        `width=${width},height=${height},top=${top},left=${left},resizable=yes,scrollbars=yes,status=yes`
    );
}

window.addEventListener("message", function(event) {
    const setup_status = document.getElementById("setup_status");
    if (event.data.type === "SQUARE_AUTH_ERROR") {
        setup_status.textContent = "System error, can not connect to Square."
        setup_status.style.color = "red"
    }
    if (event.data.type === "MISSING_COMBO_API_KEY") {
        const square_not_connected = document.getElementById("square_provider_not_connected");
        const square_connected = document.getElementById("square_provider_connected");
        const combo_not_connected = document.getElementById("combo_provider_not_connected");

        square_not_connected.style.display = "none"
        square_connected.style.display = "flex"
        combo_not_connected.style.display = "flex"

        const client_id_input = document.getElementById("client_id_input");
        client_id_input.value = event.data.client_id;

        setup_status.textContent = "Please provide combo api key to finalize setup."
        setup_status.style.color = "red"
    }
    if (event.data.type === "COMBO_API_KEY_INVALID") {
        setup_status.textContent = "Invalid combo api key."
        setup_status.style.color = "red"

        const client_id_input = document.getElementById("client_id_input");
        client_id_input.value = event.data.client_id;
    }
    if (event.data.type === "SETUP_COMPLETED") {
        const square_not_connected = document.getElementById("square_provider_not_connected");
        const square_connected = document.getElementById("square_provider_connected");

        square_not_connected.style.display = "none"
        square_connected.style.display = "flex"

        const combo_not_connected = document.getElementById("combo_provider_not_connected");
        const combo_connected = document.getElementById("combo_provider_connected");

        combo_not_connected.style.display = "none"
        combo_connected.style.display = "flex"

        setup_status.textContent = "Your integration is fully operational."
        setup_status.style.color = "green"
    }
});

document.getElementById("comboForm").addEventListener("submit", function (e) {
    window.open("", "comboPopup", "width=100,height=100");
});