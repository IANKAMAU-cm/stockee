document.addEventListener("DOMContentLoaded", function() {
    const loginForm = document.querySelector("form");

    loginForm.addEventListener("submit", function(event) {
        event.preventDefault();

        const username = document.getElementById("username").value;
        const password = document.getElementById("password").value;

        //additional client-side validation before sending the form
        if (username && password) {
            loginForm.submit();
        } else {
            alert("Please enter both username and password.");
        }

    });
});