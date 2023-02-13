var charts = []

function get_plots()
$.ajax({
    url: "http://localhost/plots",
    type: "GET",
    dataType: 'json',
    success: () => {}
});