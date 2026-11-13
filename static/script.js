document.querySelectorAll(".delete-form").forEach(function(form) {
    form.addEventListener("submit", function(event) {
        if (!confirm("Are you sure you want to delete this task?")) {
            event.preventDefault();
        }
    });
});

var searchInput = document.querySelector("#task-search");
var statusFilter = document.querySelector("#status-filter");

function filterTasks() {
    var query = searchInput.value.trim().toLowerCase();
    var status = statusFilter.value;
    var visibleTasks = 0;

    document.querySelectorAll(".task-card").forEach(function(card) {
        var matchesSearch = card.dataset.search.includes(query);
        var matchesStatus = status === "all" || card.dataset.status === status;
        var isVisible = matchesSearch && matchesStatus;
        card.hidden = !isVisible;
        if (isVisible) {
            visibleTasks += 1;
        }
    });

    document.querySelector("#no-search-results").hidden = visibleTasks > 0;
}

if (searchInput && statusFilter) {
    searchInput.addEventListener("input", filterTasks);
    statusFilter.addEventListener("change", filterTasks);
}