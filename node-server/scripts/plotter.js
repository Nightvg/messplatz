var yAxises = [];
var xAxis;
var chart;
var root;
var sers = [];
var attempts = 0;
var emptyData = [{}];

function addData(data) {
    sers.forEach((series) => {
        //TODO -> Animation not working properly, still working like this so leave it as comment for now
        //let lastValue = series.dataItems[series.dataItems.length - 1];
        series.data.pushAll(data);
        //Shift Series in case of overflow
        for(;series.data.length > 9e6; series.data.shift());
        // let newValue = series.dataItems[series.dataItems.length - 1];
        // newValue.animate({
        //     key: "valueYWorking",
        //     to: newValue,
        //     from: lastValue,
        //     duration: 33,
        //     easing: am5.ease.linear
        // });
    });
}

function createSeries(name, field, yAxis) {
    let series = chart.series.push(
        am5xy.LineSeries.new(root, {
            name: name,
            xAxis: xAxis,
            yAxis: yAxis,
            valueYField: field,
            valueXField: "timestamp",
            stroke: am5.color(0x0000aa)
            }
        )
    );
    series.data.processor = am5.DataProcessor.new(root, {
        numericFields: [field],
        dateField: ["timestamp"]
    });    
    series.strokes.template.set("strokeWidth", 2);
    series.data.setAll(emptyData);
    sers.push(series);
}

function poll() {
    setTimeout(function() {
        $.ajax({
            url: "http://localhost/data",
            type: "GET",
            dataType: "json",
            success: (data) => {
                if(data.length > 0){
                    data.forEach(elem => {elem.timestamp *= 1000;});
                    addData(data);
                    attempts = 0;
                }
                else attempts++;
            },
            complete: poll,
            error: (jqXHR, textStatus, errorThrown) => {
                console.log(errorThrown)
                attempts++;
            }
        });

    }, 34<<Math.min(attempts,6));
}

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
            min: new Date().getTime(),
            extraMax: 0.2,
            baseInterval: {
                timeUnit: "millisecond",
                count: 1
            },
            renderer: am5xy.AxisRendererX.new(root, {}),
            tooltip: am5.Tooltip.new(root, {})
        }));
        xAxis.data.setAll(emptyData);
        xAxis.get("dateFormats")["second"] = "HH:mm:ss.SSS";

        //Y-Axis
        let labels = ['EMG1', 'EMG2', 'ECG', 'BR', 'EDA'];
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
