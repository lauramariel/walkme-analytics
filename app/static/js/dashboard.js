function numberCountdown(element) {
    if (!element.classList.contains('started')) {
        element.classList.add('started');
        var interval = setInterval(function() {
            remaining = element.innerHTML;
            hours = parseInt(remaining.split(':')[0]);
            minutes = parseInt(remaining.split(':')[1]);
            if(minutes == 0) {
                if (hours > 0) {
                    hours--;
                    minutes=60;
                }
            }
            minutes--;
            // Move the setWarning down here, that way it happens even if the page is refreshed
            if (hours == 0) {
                setWarning(element);
            }
            if (hours <= 0 && minutes == 0 ) {
                element.innerHTML = "Expired";
                clearInterval(interval);
                setExpired(element);
            } else {
                element.innerHTML = hours.toString() + ":" + pad(minutes.toString(),2);
            }
        }, 60000);
    }
}

function circleCountdown(element) {
    var radius = element.r.baseVal.value;
    var circumference = radius * 2 * Math.PI;
    element.style.strokeDasharray = `${circumference} ${circumference}`;
    
    if (! element.classList.contains('started')) {
        element.classList.add('started');
        var progInt = setInterval(function() 
        {
            var xp = element.getAttribute('id');

            // Circle countdown process is the same for provisioning and for test drive time remaining (uses tdstatus)
            jQuery.get('tdstatus/' + xp, function(newProg) {
                if((! newProg ) || (newProg['status'] >= 100)) {
                    location.reload(true);
                } else {
                    var prog = 0;
                    if (element.getAttribute('class').includes('td-provision-circle')) {
                        prog = newProg['status'];
                    }
                    else {
                        prog = newProg['percent_left'];
                    }
                    var offset = circumference - prog / 100 * circumference;
                    element.style.strokeDashoffset = offset;
                }});
        }, 120000);    
    }
}

function setExpired(element) {
    thisRow = element.parentElement.parentElement;
    thisRow.classList.remove('warning');
    thisRow.classList.add('expired');
    thisRow.lastElementChild.innerHTML = '<div class="card-body pt-4 pb-1 text-center"><a href="https://www.nutanix.com/test-drive-hyperconverged-infrastructure" class=\'btn btn-primary connect-button\'>Request New Test Drive</a></div>';
}
function setWarning(element) {
    thisRow = element.parentElement.parentElement;
    if (!thisRow.className.includes('warning')) {
        thisRow.classList.remove('active');
        thisRow.classList.add('warning');
        theButton = element.parentElement.parentElement.lastElementChild.lastElementChild;
        theButton.classList.remove('btn-success');
        theButton.classList.add('btn-warning');
    }
}

function pad(num, size){ return ('000000000' + num).substr(-size); } 

function init() {
    // Load the data variables
    var xp_launch = document.getElementById("dashboardjs").getAttribute("data-launch")
    var xp_guide = document.getElementById("dashboardjs").getAttribute("data-guide")
    if (xp_launch != "") {
        if (xp_guide != "") {
            window.open(xp_guide, "_blank");
        }
        window.location = xp_launch;
        return false;
    }

    // Init the test drive time circles
    var circles = document.getElementsByClassName("td-remaining-circle");
    for (e = 0; e < circles.length; e++) {
        circleCountdown(circles[e]);
    }

    // Init the provisioning circles
    var prog = document.getElementsByClassName("td-provision-circle");
    for (f = 0; f < prog.length; f++) {
        circleCountdown(prog[f]);
    }
    // Init the expiration timers
    var timers = document.getElementsByClassName("td-timer");
    for (i = 0; i < timers.length; i++) {
        numberCountdown(timers[i]);
    }
}
window.addEventListener("load", init, false);
