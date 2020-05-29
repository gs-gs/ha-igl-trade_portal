var gulp = require('gulp');
var sass = require('gulp-sass');
var sourcemaps = require('gulp-sourcemaps');
var uglify = require('gulp-uglify');
var rename = require('gulp-rename');
var cp = require('child_process');
var concatjs = require('gulp-concat');
var browserSync = require('browser-sync').create();
var iconfont = require('gulp-iconfont');
var iconfontCss = require('gulp-iconfont-css');
var runTimestamp = Math.round(Date.now()/1000);
var imagemin = require('gulp-imagemin');
var imageminMozjpeg = require('imagemin-mozjpeg');

var paths = {
    styles: {
        src: 'trade_portal/static/sass/**/*.scss',
        dest: 'trade_portal/static/css'
    },
    scripts: {
        src: 'trade_portal/static/_js/*.js',
        dest: 'trade_portal/static/js/'
    },
    images: {
        src: 'trade_portal/static/images/**/*.*',
        dest: 'trade_portal/static/images/'
    }
};

function style() {
    return gulp.src(
        paths.styles.src
    )
        .pipe(sourcemaps.init())

        .pipe(sass({
            includePaths: ['node_modules/bootstrap/scss/'],
            outputStyle: 'compressed',
            onError: browserSync.notify
        }))
        .pipe(sourcemaps.write('.'))
        .pipe(gulp.dest(paths.styles.dest))
        .pipe(browserSync.reload({stream:true}));
}

function js() {
    return gulp.src([
        './node_modules/jquery/dist/jquery.min.js',
        './node_modules/bootstrap/dist/js/bootstrap.js',
        paths.scripts.src
    ])
        .pipe(sourcemaps.init())
        .pipe(concatjs('scripts.js'))
        .pipe(sourcemaps.write('.'))
        .pipe(gulp.dest(paths.scripts.dest))
        .pipe(browserSync.reload({stream:true}))
}

function minifyJs() {
    return gulp.src([
        paths.scripts.dest + '*.js'
    ])
        .pipe(uglify())
        .pipe(rename({ suffix: '.min' }))
        .pipe(gulp.dest(paths.scripts.dest));
}

function optimiseImages() {
    return gulp.src('images/**/*')
        .pipe(imagemin([
            imagemin.optipng({optimizationLevel: 5}),
            imageminMozjpeg({
                quality: 90
            }),
            imagemin.svgo({
                plugins: [
                    {removeUnknownsAndDefaults: false}
                ]
            })
        ]))
        .pipe(gulp.dest(paths.images.dest));
}

function optimiseUploads() {
    return gulp.src(paths.uploads.src)
        .pipe(imagemin([
            imageminMozjpeg({
                quality: 90
            }),
            imagemin.optipng(),
            imagemin.svgo({
                plugins: [
                    {removeUnknownsAndDefaults: false},
                    {allowEmpty: true}
                ]
            })
        ]))
        .pipe(gulp.dest(paths.uploads.dest));
}

function browserSyncServe(done) {
    browserSync.init({
        proxy: "localhost:8050"
    });
    done();
}

function browserSyncReload(done) {
    browserSync.reload();
    done();
}

function watch() {
    gulp.watch(paths.styles.src, style);
    gulp.watch(paths.scripts.src, js);
    gulp.watch(
        [
            'trade_portal/templates/**/*.html'
        ],
        gulp.series(browserSyncReload));
}

function fontIcons(){
    var fontName = 'traded-icons';

    return gulp.src(['trade_portal/static/images/font-icons/*.svg'])
        .pipe(iconfontCss({
            fontName: fontName,
            path: 'trade_portal/static/sass/mixins/_icons-template.scss',
            targetPath: '../sass/_icons.scss',
            fontPath: '../fonts/',
            cssClass: 'icon',
            cacheBuster: runTimestamp
        }))
        .pipe(iconfont({
            fontName: fontName,
            formats: ['svg', 'ttf', 'eot', 'woff', 'woff2'],
            fontPath: '../fonts/',
            normalize: true,
            fontHeight: 1500
        }))
        .pipe(gulp.dest('trade_portal/static/fonts/'));
}


gulp.task('icons', gulp.series(fontIcons));
gulp.task('images', gulp.parallel(optimiseImages, optimiseUploads));
gulp.task('styles', gulp.series(style));
gulp.task('js', gulp.series(js));
gulp.task('build', gulp.series(fontIcons, gulp.parallel(style, js), minifyJs));
gulp.task('dev', gulp.series(gulp.parallel(style, js), browserSyncServe, watch));
gulp.task('default', gulp.series(gulp.parallel(style, js), browserSyncServe, watch));