//active navbar
let nav = document.querySelector(".navigation-wrap");
window.onscroll = function() {
    if (document.documentElement.scrollTop > 20) {
        nav.classList.add("scroll-on");
    } else {
        nav.classList.remove("scroll-on");
    }
}


//nav hide
let navBar = document.querySelectorAll('.nav-link');
let navCollapse = document.querySelector('.navbar-collapse.collapse');
navBar.forEach(function(a) {
    a.addEventListener("click", function() {
        navCollapse.classList.remove("show");
    })
})

//counter design

/*===== products =====*/
var button = document.getElementById("enter");
var input = document.getElementById("userinput");
var ul = document.querySelector("ul");

button.addEventListener("click", function() {
    var li = document.createElement("li");
    li.className = 'list-group-item';
    li.textContent = input.value;
    ul.appendChild(li);
});