var yAxises = [];
var xAxis;
var chart;
var root;

function addData(data) {
    chart.series.values.forEach((series) => {
        console.log(data);
        let lastValue = series.dataItems[series.dataItems.length - 1];
        series.data.pushAll(data);
        //Shift Series in case of overflow
        for(;series.data.length > 9e6; series.data.shift());
        let newValue = series.dataItems[series.dataItems.length - 1];
        newValue.animate({
            key: "valueYWorking",
            to: newValue.get("valueX"),
            from: lastValue.get("valueX"),
            duration: 33,
            easing: am5.ease.linear
        });
    });
}

function createSeries(name, field, yAxis) {
    let series = chart.series.push(
        am5xy.LineSeries.new(root, {
            name: name,
            xAxis: xAxis,
            yAxis: yAxis,
            valueYField: field,
            valueXField: "date",
            clustered: false
            }
        )
    );
    series.data.processor = am5.DataProcessor.new(root, {
        numericFields: [field],
        dateField: ["timestamp"]
    });    
}

function poll() {
    setTimeout(function() {
        $.ajax({
            url: "http://localhost/data",
            type: "GET",
            dataType: "json",
            success: (data) => {
                data.timestamp = data.timestamp.map(elem => new Date(elem*1000));
                addData(data);
            },
            complete: poll,
            error: (jqXHR, textStatus, errorThrown) => {
                console.log(errorThrown)
            }
        });
        // am5.net.load("/data").then(data => {
        //     console.log(data);
        //     data.timestamp = data.timestamp.map(elem => new Date(elem*1000));
        //     addData(data);
        //     poll();
        // });
    }, 33);
}

// function syncTitles() {
//     var g1w = yAxises[0].ghostLabel.width();
//     let max = 0
//     for(let i = 1; i < 5; i++)
//     {
//         let tmp = yAxises[i].ghostLabel.width();
//         max = Math.max(g1w, tmp);
//     }
  
//     yAxises[0].ghostLabel.set("minWidth", max)
//     yAxises[1].ghostLabel.set("minWidth", max)
//     yAxises[2].ghostLabel.set("minWidth", max)
//     yAxises[3].ghostLabel.set("minWidth", max)
//     yAxises[4].ghostLabel.set("minWidth", max)
// }

window.onload = () => {
    am5.ready(function() {
        // Create root element
        // https://www.amcharts.com/docs/v5/getting-started/#Root_element
        root = am5.Root.new("chart");

        // Set themes
        // https://www.amcharts.com/docs/v5/concepts/themes/
        root.setThemes([
        am5themes_Animated.new(root)
        ]);

        // Create chart
        // https://www.amcharts.com/docs/v5/charts/xy-chart/
        chart = root.container.children.push(am5xy.XYChart.new(root, {
            layout: root.verticalLayout
        }));

        // Create axes
        // https://www.amcharts.com/docs/v5/charts/xy-chart/axes/
        xAxis = chart.xAxes.push(am5xy.DateAxis.new(root, {
            groupData: false,
            baseInterval: {
                timeUnit: "second",
                count: 30
            },
            renderer: am5xy.AxisRendererX.new(root, {
                minGridDistance: 10
            }),
            tooltip: am5.Tooltip.new(root, {})
        }));
        xAxis.get("dateFormats")["second"] = "HH:mm:ss.SSS"

        //Y-Axis
        let labels = ['EMG1', 'EMG2', 'ECG', 'BR', 'EDA']
        for(let i = 0; i < 5; i++)
        {
            tmpAxis = chart.yAxes.push(
                am5xy.ValueAxis.new(root, {
                x: am5.percent(100),
                centerX: am5.percent(100),
                renderer: am5xy.AxisRendererY.new(root, {})
                })
            );
            tmpLabel = am5.Label.new(root, {
                rotation: -90,
                text: labels[i],
                y: am5.p50,
                centerX: am5.p50
            })
            // tmpAxis.ghostLabel.events.on("boundschanged", function() {
            //     syncTitles()
            // })
            tmpAxis.children.unshift(
                tmpLabel
            );
            if(i > 0)
            {
                tmpAxis.axisHeader.set("paddingTop", 10);
                tmpAxis.axisHeader.children.push(am5.Label.new(root, {
                    fontWeight: "500"
                }));
            }
            yAxises.push(tmpAxis);
        }

        chart.leftAxesContainer.set("layout", root.verticalLayout);
        // Add cursor
        // https://www.amcharts.com/docs/v5/charts/xy-chart/cursor/
        var cursor = chart.set("cursor", am5xy.XYCursor.new(root, {
            xAxis: xAxis
        }));
        cursor.lineY.set("visible", true);

        createSeries("EMG1", "EMG1", yAxises[0]);
        createSeries("EMG2", "EMG2", yAxises[1]);
        createSeries("ECG", "ECG", yAxises[2]);
        createSeries("BR", "BR", yAxises[3]);
        createSeries("EDA", "EDA", yAxises[4]);


        // Make stuff animate on load
        // https://www.amcharts.com/docs/v5/concepts/animations/
        chart.appear(1000, 100);
        poll();
    });
}
