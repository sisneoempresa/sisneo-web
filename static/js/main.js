(function () {
  "use strict";
  var burger = document.querySelector(".burger");
  var menu = document.getElementById("menu");
  if (burger && menu) {
    burger.addEventListener("click", function () {
      var open = menu.classList.toggle("open");
      burger.setAttribute("aria-expanded", open ? "true" : "false");
      burger.setAttribute("aria-label", open ? "Fechar menu" : "Abrir menu");
    });
    menu.addEventListener("click", function (e) {
      if (e.target.tagName === "A") {
        menu.classList.remove("open");
        burger.setAttribute("aria-expanded", "false");
      }
    });
  }

  // Dica do WhatsApp: aparece após alguns segundos e fica fechada depois de dispensada
  var tip = document.getElementById("wa-tip");
  var KEY = "sisneo_wa_tip";
  if (tip) {
    var dismissed = false;
    try { dismissed = window.localStorage.getItem(KEY) === "1"; } catch (e) {}
    if (!dismissed) {
      setTimeout(function () { tip.hidden = false; }, 4000);
    }
    var x = tip.querySelector(".wa-x");
    if (x) {
      x.addEventListener("click", function () {
        tip.hidden = true;
        try { window.localStorage.setItem(KEY, "1"); } catch (e) {}
      });
    }
  }

  // Máscara simples de telefone
  var tel = document.getElementById("whatsapp");
  if (tel) {
    tel.addEventListener("input", function () {
      var d = tel.value.replace(/\D/g, "").slice(0, 11);
      var out = d;
      if (d.length > 6) {
        out = "(" + d.slice(0, 2) + ") " + d.slice(2, d.length - 4) + "-" + d.slice(-4);
      } else if (d.length > 2) {
        out = "(" + d.slice(0, 2) + ") " + d.slice(2);
      }
      tel.value = out;
    });
  }

  // Evita envio duplo e leva o foco aos erros do servidor
  var form = document.querySelector("form.form");
  if (form) {
    form.addEventListener("submit", function () {
      var b = form.querySelector("button[type=submit]");
      if (b) { b.disabled = true; b.textContent = "Enviando..."; }
    });
  }
  var err = document.getElementById("form-errors");
  if (err) {
    err.scrollIntoView({ block: "center" });
    err.focus({ preventScroll: true });
  }
})();
