/**
 * REUSABLE LIS FILTER ENGINE
 * Use this for Laboratory, Phlebotomy, and Results pages.
 */
window.initLISFilter = function(elementId, onApplyCallback) {
    const checkDeps = setInterval(() => {
        if (window.jQuery && window.moment && jQuery.fn.daterangepicker) {
            clearInterval(checkDeps);
            setupPicker();
        }
    }, 50);

    function setupPicker() {
        const $picker = $(elementId);
        if (!$picker.length) return;

        const start = moment().subtract(29, 'days');
        const end = moment();

        $picker.daterangepicker({
            startDate: start,
            endDate: end,
            ranges: {
                'Today': [moment(), moment()],
                'Last 7 Days': [moment().subtract(6, 'days'), moment()],
                'Last 30 Days': [moment().subtract(29, 'days'), moment()],
                'This Month': [moment().startOf('month'), moment().endOf('month')]
            }
        }, function(start, end) {
            // Update Label
            const display = start.format('MMMM D, YYYY') + ' - ' + end.format('MMMM D, YYYY');
            $picker.find('.reportrange-picker-field').text(display);
            
            // Execute the page-specific refresh
            onApplyCallback(start, end);
        });

        // Set Initial UI
        $picker.find('.reportrange-picker-field').text(start.format('MMMM D, YYYY') + ' - ' + end.format('MMMM D, YYYY'));
    }
};