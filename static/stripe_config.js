fetch("/config/")
.then((result) => { return result.json(); })
.then((data) => {
    const stripe = Stripe(data.publicKey);

    document.querySelector("#submitBtn").addEventListener("click", () => {
    const catId = document.querySelector("#submitBtn").getAttribute("data-cat-id");
    console.log('Cat ID:', catId); // Debugging line to check the value
    fetch(`/create-checkout-session/?cat_id=${catId}`)
        .then((result) => { return result.json(); })
        .then((data) => {
            console.log(data);
            return stripe.redirectToCheckout({sessionId: data.sessionId});
        })
        .then((res) => {
            console.log(res);
        });
    });
});