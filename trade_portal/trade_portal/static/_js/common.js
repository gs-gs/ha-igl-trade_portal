jQuery(document).ready(function ($) {
    $('#mainMenu').on('shown.bs.collapse', function () {
        $('.site-nav__overlay').addClass('active');
    });
    $('#mainMenu').on('hidden.bs.collapse', function () {
        $('.site-nav__overlay').removeClass('active');
    });

    $('.site-nav__overlay').on('click', function (e) {
        $('#mainMenu').collapse('hide');
    });

    $('[data-toggle="qr"]').popover({
        html: true,
        placement: 'left',
        content: function () { return $('#' + $(this).data('qr')).html();  }
    });

    $('[data-toggle="tooltip"]').tooltip();

    $('body').on('click', function (e) {
        //did not click a popover toggle, or icon in popover toggle, or popover
        if ($(e.target).data('toggle') !== 'qr'
            && $(e.target).parents('[data-toggle="qr"]').length === 0
            && $(e.target).parents('.popover.in').length === 0) {
            $('[data-toggle="qr"]').popover('hide');
        }
    });

});

function copyToClipboard(fieldId){
    var copyText = document.getElementById(fieldId);

    copyText.select();
    copyText.setSelectionRange(0, 99999); /*For mobile devices*/

    document.execCommand("copy");

    /* Alert the copied text */
    alert("Copied the text: " + copyText.value);
}