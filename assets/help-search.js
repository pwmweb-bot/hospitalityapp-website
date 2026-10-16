(function () {
  var input = document.getElementById("help-q");
  var results = document.getElementById("help-results");
  if (!input || !results) return;
  var articles = [];

  fetch("/help/search.json")
    .then(function (response) { return response.json(); })
    .then(function (data) { articles = data.articles || []; })
    .catch(function () { articles = []; });

  function show(matches, query) {
    if (!query) {
      results.hidden = true;
      results.innerHTML = "";
      return;
    }
    results.hidden = false;
    if (!matches.length) {
      results.innerHTML = '<p class="hc-empty">No guides match that.</p>';
      return;
    }
    results.innerHTML = matches.slice(0, 8).map(function (article) {
      return '<a href="' + article.url + '"><strong>' + article.title + '</strong><span>' +
        article.topicTitle + " · " + article.summary + "</span></a>";
    }).join("");
  }

  input.form.addEventListener("submit", function (event) { event.preventDefault(); });

  input.addEventListener("input", function () {
    var query = input.value.trim().toLowerCase();
    if (query.length < 2) {
      show([], "");
      return;
    }
    var matches = articles.filter(function (article) {
      return (article.title + " " + article.summary + " " + article.text).toLowerCase().indexOf(query) !== -1;
    });
    show(matches, query);
  });

  document.addEventListener("keydown", function (event) {
    if (event.key === "/" && document.activeElement !== input) {
      event.preventDefault();
      input.focus();
    }
  });
})();
