var gulp = require('gulp');
var sass = require('gulp-sass');
var sourcemaps = require('gulp-sourcemaps');
var uglify = require('gulp-uglify');
var rename = require('gulp-rename');
var concatjs = require('gulp-concat');
var browserSync = require('browser-sync').create();

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
            'trade_portal/**/*.html'
        ],
        gulp.series(browserSyncReload));
}

gulp.task('styles', gulp.series(style));
gulp.task('js', gulp.series(js));
gulp.task('build', gulp.series(gulp.parallel(style, js), minifyJs));
gulp.task('dev', gulp.series(gulp.parallel(style, js), browserSyncServe, watch));
gulp.task('default', gulp.series(gulp.parallel(style, js), browserSyncServe, watch));