jQuery(document).ready(function ($) {
    $('#mainMenu').on('shown.bs.collapse', function () {
        $('.site-nav__overlay').addClass('active');
    });
    $('#mainMenu').on('hidden.bs.collapse', function () {
        $('.site-nav__overlay').removeClass('active');
    });

    $('.site-nav__overlay').on('click', function (e) {
        $('#mainMenu').collapse('hide');
    })

});