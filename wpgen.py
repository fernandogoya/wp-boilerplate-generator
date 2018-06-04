#!/usr/bin/env python3

# É preciso já ter instalado a dependência "npm-check-updates"

import sys
import os
import pymysql
import shutil
from pathlib import Path
from argparse import ArgumentParser
from getpass import getpass

#Variáveis iniciais
server_path = Path("/Users/goya/WebServer")

def newFiles(fileName, content):
    f = open(fileName, 'w')
    f.write(content)
    f.close()


def prerequisites_met():
    # Verifica se o WP-CLI e Composer estão instalados. Caso estejam instalados, o PATH não será mostrado na tela.
    if not shutil.which('wp'):
        print("\n  Para executar esta instalação, é necessário ter o WP-CLI instalado.\n  Faça o download do arquivo no site http://wp-cli.org/#installing\n\n")
        sys.exit()

    if not shutil.which('composer'):
        print("\n  Para executar esta instalação, é necessário ter o Composer instalado.\n  Faça o download do arquivo no site https://getcomposer.org/download\n\n")
        sys.exit()

    return True


def create_database(args):
    print(">> Configurando o banco de dados...\n")

    args.wp_db_name = input('Nome do banco de dados: ')
    args.wp_db_prefix = input('Prefixo da tabela: ')
    
    print('\n')

    args.db_user = input('Usuário: ')
    args.db_passwd = getpass('Senha: ')

    conn = pymysql.connect(host=args.db_host, user=args.db_user, passwd=args.db_passwd)
    cursor = conn.cursor()

    stmt = f"SHOW DATABASES LIKE '{args.wp_db_name}'"
    cursor.execute(stmt)
    result = cursor.fetchone()

    if result:
        print(f'O banco de dados "{args.wp_db_name}" já existe. Escolha outro nome.')
    else:
        cursor.execute(f"CREATE DATABASE {args.wp_db_name} CHARACTER SET utf8 COLLATE utf8_general_ci")
        cursor.execute(f"ALTER USER {args.db_user}@localhost IDENTIFIED BY '{args.db_passwd}'")


# Cria os diretórios necessários
def make_folders(args):
    os.makedirs(args.path / args.proj_dir)

    location = args.path / args.proj_dir / "wp-content" / "themes" / args.theme_dir
    os.makedirs(location)

    folders = ["assets/css", "assets/js", "assets/images", "assets/images/icons", "assets/inc", "src/sass", "src/js", "config", "config/core", "config/custom", "config/setup"]
    for folder in folders:
        os.makedirs(location / folder)


# Download do WordPress
def download_wp(args):
    print('\n###########################\n## Download do WordPress ##\n###########################\n')

    # Acessa a pasta do projeto
    os.chdir(args.path / args.proj_dir)
    
    # Faz o download do WordPress
    os.system('wp core download')
    
    # Exclui o arquivo
    os.remove("wp-config-sample.php")

    print("\n>> Instalação do WordPress concluída.\n")


# Cria o arquivo wp-config
def configure_wp_core(args):
    os.system(f"""wp core config --dbname='{args.wp_db_name}' --dbuser='{args.db_user}' --dbpass='{args.db_passwd}' --dbhost='{args.db_host}' --dbprefix='{args.wp_db_prefix}'""")
    print("\n")


def write_htaccess(args):
    print('>> Gerando o htaccess\n')

    # Cria o arquivo htaccess
    htaccessContent = """<IfModule mod_rewrite.c>
RewriteEngine On
RewriteBase /{proj}/
RewriteRule ^index\.php$ - [L]
RewriteCond %{{REQUEST_FILENAME}} !-f
RewriteCond %{{REQUEST_FILENAME}} !-d
RewriteRule . /{proj}/index.php [L]
</IfModule>""".format(proj=args.proj_dir)
    newFiles(".htaccess", htaccessContent)


def create_wp_tables(args):
    print('>> Gerando tabelas do bando de dados\n')

    # Configuração do Wordpress
    os.system(f"wp core install --url='{args.urlBase + '/' + args.proj_dir}' --title='{args.wp_title}' --admin_user='{args.wp_user_login}' --admin_password='{args.wp_user_passwd}' --admin_email='{args.wp_user_email}'")
    print("\n")
    # Configura o Permalink para URL amigável
    os.system("wp rewrite structure '/%postname%/' --hard; wp rewrite flush --hard")
    print("\n")


def cleanup_folders(args):
    os.chdir(args.path / args.proj_dir / "wp-content" / "themes")
    os.system("rm -rf twentyfifteen; rm -rf twentysixteen;")


def final_wordpress_setup_steps(args):

    # Exclui todos os Posts
    os.system("wp post delete 1 --force; wp post delete 2 --force")
    print("\n")
    
    # Exclui os Plugins padrão do WordPress
    os.system("wp plugin delete hello; wp plugin delete akismet")
    print("\n")
       
    # Ativa o Tema criado
    os.system(f"wp theme activate {args.theme_dir}")

    # Configura o Timezone para o Japão 
    os.system("wp option update timezone_string Asia/Tokyo;")

    # Páginas inicial: Contato
    os.system("wp post create --post_type=page --post_title='Contato' --post_status=publish;")

    # Menu inicial
    os.system('wp menu create "Principal"; wp menu item add-post Principal 3 --title="Contato";')


# Atribui o menu como principal
def menu_inicial():
    os.system('wp menu location assign Principal primary;')
    

# Cria os arquivos do Tema:
def add_template_files(args):

    root = args.path / args.proj_dir / "wp-content" / "themes" / args.theme_dir

    # Namespaces files ################################################

    # config/ini.php
    namespaceIni = """<?php

namespace config;

use config\setup\enqueue;
use config\setup\setup;
use config\setup\header;
use config\setup\menus;


class init {

    private static $loaded = false;

    public function __construct()
    {
        $this->initClasses();
    }

    public function initClasses()
    {
    
        if(self::$loaded) {
            return;
        }

        self::$loaded = true;

        new enqueue();
        new setup();
        new header();
        new menus();
    
    }

}
"""
    newFiles(root / 'config/init.php', namespaceIni)


    # config/custom/posts.php
    namespacePosts = """<?php

namespace config\custom;

class posts {

    /**
     * Custom query to get the posts or posts according with a category
     * 
     * @author Fernando Goya
     * @since 2018-04-20
     * @param string $type Type of the content: Post, Page, etc
     * @param string $postPerPage Amount o posts per page. -1 bring all posts.
     * @param int $category Category ID
     * @param int $offSet Exclude the fisrt X post from the query 
     */
    static function get_post($postType = NULL, $postPerPage = NULL, $category = NULL, $offSet = NULL )
    {

        if ($postType == NULL && $postPerPage == NULL && $category == NULL && $offSet == NULL ) {
                
            if (have_posts()) {
                
                while (have_posts()) {
                    the_post();

                    echo
                        '<div class="post-frame">' .
                            '<article>' . 
                                '<a href="'. get_the_permalink() . '">' .  
                                    get_the_post_thumbnail(get_the_ID(), 'thumbnail') . 
                                    '<h3>' . get_the_title(). '</h3>' . 
                                    '<p>' . get_the_excerpt() . '</p>' .
                                    '<p>' . get_cat_name(get_the_category()[0]->parent) . '</p>
                                </a>
                            </article>
                        </div>';
                }
            } 
            else {
                echo '<p>No content found</p>';
            }
          
        }
        else {

            echo '<h2>' . get_the_category_by_ID($category) . '</h2>';

            $args = array(
                'post_type'      => $postType,
                'posts_per_page' => $postPerPage,
                'cat'            => $category,
                'offset'         => $offSet
            );

            $posts = new \WP_Query($args);

            if ($posts->have_posts()) {

                while ($posts->have_posts()) {
                    $posts->the_post();
                    
                    echo
                        '<div class="post-frame">' .
                            '<article id="post-'. get_the_ID() .'">' . 
                                '<a href="'. get_the_permalink() . '">' .  
                                    the_post_thumbnail('thumbnail') . 
                                    '<h3>' . get_the_title(). '</h3>' . 
                                    '<p>' . get_the_excerpt("read more") . '</p>       
                                </a>
                            </article>
                        </div>';     

                }
    
            } 
            else {
                echo '<p>No content found</p>';

            } 

            wp_reset_postdata();
        
        }

    }

    /**
     * Get the single post content
     * 
     * @author Fernando Goya
     * @since 2018-04-26
     */
    static function post()
    {
        if (have_posts()) {

            while (have_posts()) {
                the_post();
                
                echo
                    '<div class="">' .
                        '<article id="post-'. get_the_ID() .'">'.
                            get_the_post_thumbnail(get_the_ID(), "Featured Image") .
                            '<h3>' . get_the_title(). '</h3>' .
                            apply_filters('the_content', get_the_content()) .
                        '</article>
                    </div>';     

            }

        } 

    }

}
"""
    newFiles(root / 'config/custom/posts.php', namespacePosts)


    # config/setup/enqueue.php
    namespaceEnqueue = """<?php

namespace config\setup;

class enqueue {

    public function __construct()
    {
        add_action('wp_enqueue_scripts', array(&$this, 'enqueue_scripts'));
    }

    public function enqueue_scripts()
    {
 
        // css
        wp_enqueue_style( 'main', get_template_directory_uri() . '/assets/css/main.min.css', array(), NULL, 'all' );
        
        // js
        wp_enqueue_script( 'main', get_template_directory_uri() . '/assets/js/main.min.js', array(), NULL, true );
 
    }

}
"""
    newFiles(root / 'config/setup/enqueue.php', namespaceEnqueue)


    # config/core/walker.php
    namespaceWalker = """<?php

/*
    wp_nav_menu()

    <div class="menu-container">
        <ul> // start_lvl()
        
            <li><a href=""><span> // start_el()
            
                </span></a></li> // end_el()
            
            <li><a href="">Link</a></li>
            <li><a href="">Link</a></li>
        
        </ul> // end_lvl()

    </div>
*/

namespace config\core;

use Walker_Nav_Menu;

class Walker extends Walker_Nav_Menu {

    protected $sub_menu = ' sub-menu';
    protected $dropdown = 'dropdown';
    protected $dropdown_menu = 'dropdown-menu';
    protected $dropdown_toggle = 'dropdown-toggle';
    protected $dropdown_sub_menu_icon = 'dropdown-icon';
    protected $active = 'active';
    
    public function start_lvl(&$output, $depth = 0, $args = array())
    {
        $indent = str_repeat("\\t", $depth);
        $submenu = ($depth > 0) ? $this->sub_menu : '';
        $output .= "\\n$indent<ul class=\\"$this->dropdown_menu$submenu depth_$depth\\" >\\n";

    }

    public function start_el(&$output, $item, $depth = 0, $args = array(), $id = 0)
    {
        $ident = ($depth) ? str_repeat("\\t", $depth) : '';

        $li_attributes = '';
        $class_names = $value = '';

        $classes = empty($item->classess) ? array() : (array) $item->classes;
        
        $classes[] = ($args->walker->has_children) ? $this->dropdown : '';
        $classes[] = ($item->current || $item->current_item_anchestor) ? $this->active : '';
        $classes[] = 'menu-item-' . $item->ID;
        if ($depth && $args->walker->has_children) {
            $classes[] = $this->dropdown_menu;
        }

        $class_names = join(' ', apply_filters('nav_menu_css_class', array_filter($classes), $item, $args));
        $class_names = ' class="' . esc_attr($class_names) . '"';

        $id = apply_filters('nav_menu_item_id', 'meni-item-'.$item->ID, $item, $args);
        $id = strlen($id) ? ' id="' . esc_attr($id) . '"' : '';

        $output .= $ident . '<li' . $id . $value . $class_names . $li_attributes . '>';

        $attibutes = !empty($item->attr_title) ? ' title="' . esc_attr($item->attr_title) . '"' : '';
        $attibutes .= !empty($item->target) ? ' target="' . esc_attr($item->target) . '"' : '';
        $attibutes .= !empty($item->xfn) ? ' rel="' . esc_attr($item->xfn) . '"' : '';
        $attibutes .= !empty($item->url) ? ' href="' . esc_attr($item->url) . '"' : '';

        $attibutes .= ($args->walker->has_children) ? ' class="' . $this->dropdown_toggle . '" data-toggle="' . $this->dropdown . '$this->"' : '';

        $item_output = $args->before;
        $item_output .= '<a' . $attibutes . '>';
        $item_output .= $args->link_before . apply_filters('the_title', $item->title, $item->ID) . $args->link_before;
        $item_output .= ($depth == 0 && $args->walker->has_children) ? ' <b class="' . $this->dropdown_sub_menu_icon . '"></b></a>' : '</a>';
        $item_output .= $args->after;

        $output .= apply_filters('walker_nav_menu_start_el', $item_output, $item, $depth, $args);

    }

    /*
    public function end_el()
    {

    }

    public function end_lvl()
    {

    }
    */

}
"""
    newFiles(root / 'config/core/walker.php', namespaceWalker)


    # config/setup/header.php
    namespaceHeader = """<?php

namespace config\setup;

class header {

    public function __construct()
    {
        
    }

}
"""
    newFiles(root / 'config/setup/header.php', namespaceHeader)
    
    
    # config/setup/menu.php
    namespaceMenu = """<?php

namespace config\setup;

class menus {

    public function __construct()
    {
        add_action('after_setup_theme', array(&$this, 'menus'));
    }

    public function menus()
    {
        register_nav_menus(
            array(
                'primary' => 'Header',
                'footer' => 'Footer'
            )
        );
    }

}
"""
    newFiles(root / 'config/setup/menus.php', namespaceMenu)


    # config/setup/setup.php
    namespaceSetup = """<?php

namespace config\setup;

class setup {

    public function __construct()
    {
        add_action( 'after_setup_theme', array(&$this, 'post_format') );  
        add_action( 'after_setup_theme', array(&$this, 'featured_image') );
        add_action( 'after_setup_theme', array(&$this, 'image_sizes') );
        add_action( 'widgets_init', array(&$this, 'widget_setup'));

        add_filter( 'image_size_names_choose', array(&$this, 'attachment_image_sizes') );
        add_filter( 'excerpt_length', array(&$this, 'excerpt_length') );
        
    }

    public function post_format()
    {
        add_theme_support('post-formats', array(
            'image',
            'video',
            'audio'
        ));

    }

    // Display the Featured Image    
    public function featured_image()
    {
        add_theme_support( 'post-thumbnails' );
    }


    public function image_sizes()
    {
        add_image_size( 'movie-poster', 220, 310, true );   
        add_image_size( 'thumbnail', 380, 220, true );
        add_image_size( 'featured-image', 860, 480);
        add_image_size( 'full', 1200, 1200 );        

    }

    // Attachment display settings custom sizes
    function attachment_image_sizes( $sizes ) {
        return array_merge( $sizes, array(
          'thumbnail'    => __( 'Thumbnail' ),
          'featured-image' => __( 'Featured Image' ),
          'full' => __( 'Full' )
        ) );
    }

    // Custom excerpt length
    public function excerpt_length()
    {
        return 15;
    }


    // Widget area
    function widget_setup() {

        register_sidebar( 
            array(
                'name'          => 'Sidebar',
                'id'	        => 'sidebar',
                'class'         => 'custom',
                'description'   => 'Colocar uma descrição sobre o Sidebar. Ex.: Standard Sidebar',
                'before_widget' => '<aside id="%1$s" class="widget %2$s">',
                'after_widget'  => '</aside>',
                'before_title'  => '<h1 class="widget-title">',
                'after_title'   => '</h1>'
            )
        );	
    
    }

}

"""
    newFiles(root / 'config/setup/setup.php', namespaceSetup)


    # Theme basic files ###############################################

    # header.php
    headerContent = """<!DOCTYPE html>
<html <?php language_attributes(); ?>>
<head>
    <meta charset="<?php bloginfo('charset'); ?>">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="X-UA-Compatible" content="ie=edge">
    <meta name="apple-mobile-web-app-title" content="<?php bloginfo('name'); ?>">
    <title><?php bloginfo('name'); ?><?php wp_title('|'); ?></title>

    <?php wp_head(); ?>

</head>
<body <?php body_class(); ?>>

    <div id="wrapper">
        <nav>
            <div class="container">
                <h1>
                    <a href="<?php echo esc_url(home_url('/')); ?>">
                        <img src="<?php echo content_url('/themes/') . wp_get_theme(); ?>/assets/images/metropolis-logo.svg" class="logo" alt="<?php bloginfo('name'); ?>">
                    </a>
                </h1> 
                <?php 
                    wp_nav_menu( array(
                        'theme_location'  => 'primary',
                        'container_class' => 'navbar',
                        'menu_class'      => 'menu',
                        'walker'          => new config\core\walker()
                    ) ); 
                ?>
            </div>
        </nav>
"""


    #index.php
    indexContent = """<?php get_header(); ?>

    <div class="container">
    
       <?php config\custom\posts::get_post(); ?>

    </div>

<?php get_footer(); ?>    
"""


    # footer.php
    footerContent = """
            <footer>
            <div class="container">
                <?php wp_nav_menu(array('theme_location' => 'footer'));  ?>

                <p><?php bloginfo('name'); ?></p>
            </div>
        </footer>

    </div> <!-- #wrapper -->

    <?php wp_footer(); ?>

</body>
</html>
"""


    # style.css
    styleContent = """/*
Theme Name:  
Theme URI: 
Author: Fernando Goya
Description: 
License: 
*/
"""


    # functions.php
    functionContent = """<?php

if ( file_exists( dirname( __FILE__ ) . '/vendor/autoload.php') ):
    require_once dirname( __FILE__ ) . '/vendor/autoload.php';
endif;

if ( class_exists( 'config\\\\init' ) ):
    new \config\init();
endif;
"""


    # search.php
    searchContent = """<?php

"""


    # page.php
    pageContent = """<?php get_header(); ?>

    <div class="container">
    
       <?php config\custom\posts::post(); ?>

    </div>
    
<?php get_footer(); ?>
"""


    # single.php
    singleContent = """<?php get_header(); ?>
    
    <div class="container">

        <?php config\custom\posts::post(); ?>
    
    </div>

<?php get_footer(); ?>
"""


    files = {
        root / "header.php": headerContent,
        root / "index.php": indexContent,
        root / "footer.php": footerContent,
        root / "style.css": styleContent,
        root / "functions.php": functionContent,
        root / "search.php": searchContent,
        root / "page.php": pageContent,
        root / "single.php": singleContent,
    }
    
    # Cria os arquivos do Tema
    for k, v in files.items():
        newFiles(k, v)


    # Dependencies files #########################################

    # Composer
    composerContent = """{
    "name": "%s/composer",
    "description": "Starter Theme",
    "authors": [
        {
            "name": "Fernando",
            "email": "contato@fernandogoya.com"
        }
    ],
    "require": {
        "vlucas/phpdotenv": "^2.4"
    },
    "autoload": {
        "psr-4": {"config\\\\": "./config"}
    }
}""" % (args.theme_dir)
    newFiles(root / 'composer.json', composerContent)


    # Package.json
    packageContent = """
{
  "name": "%s",
  "version": "1.0.0",
  "description": "",
  "main": "index.js",
  "scripts": {
    "start": "gulp"
  },
  "author": "Fernando Goya",
  "license": "ISC",
  "devDependencies": {
    "gulp": "^3.9.1",
    "gulp-concat": "^2.6.1",
    "gulp-plumber": "^1.2.0",
    "gulp-sass": "^4.0.1",
    "gulp-uglify": "^3.0.0",
    "browser-sync": "^2.24.4",
    "gulp-autoprefixer": "^5.0.0"
  }
}
""" % (args.theme_dir)
    newFiles(root / 'package.json', packageContent)


    # Gulpfile.js
    gulpContent = """const gulp         = require('gulp');
const concat       = require('gulp-concat');
const plumber      = require('gulp-plumber');
const sass         = require('gulp-sass');
const uglify       = require('gulp-uglify');
const autoprefixer = require('gulp-autoprefixer');
const browserSync  = require('browser-sync').create();

const destCss      = './assets/css';
const destJs       = './assets/js';

const srcSass      = './src/sass/*.scss';
const srcJs        = './src/js/*.js';

// SASS
gulp.task('sass', ()=>{
    gulp.src(srcSass)
        .pipe(plumber())
        .pipe(sass({
            outputStyle: 'expanded' // 'compressed'
        }))
        .pipe(concat('main.min.css'))
        .pipe(autoprefixer({
            browsers: ['last 10 versions'],
            cascade: false
        }))
        .pipe(gulp.dest(destCss))
        .pipe(browserSync.stream());
});

// JavaScript
gulp.task('js', ()=>{
    gulp.src(srcJs)
        .pipe(plumber())
        .pipe(concat('main.min.js'))
        .pipe(uglify())
        .pipe(gulp.dest(destJs))
        .pipe(browserSync.stream());
});

// BrowserSync
gulp.task('server', ['sass', 'js'], ()=>{
    browserSync.init({
        proxy: '%s/%s'
    });

    gulp.watch(srcSass, ['sass']);
    gulp.watch('./**/*.php').on('change', browserSync.reload);
});

gulp.task('default', ['server']);
""" % (args.urlBase, args.proj_dir)
    newFiles(root / 'gulpfile.js', gulpContent)


    # SASS file ##################################################

    # _setup.scss
    sassSetup = """* {
    box-sizing: border-box;
}

html, body {
    margin: 0;
    padding: 0;
    font-family: $body-font-family;
}

body {
    background-color: $body-color;
}
"""
    newFiles(root / 'src/sass/_setup.scss', sassSetup)

    # _menu.scss
    sassMenu = """nav {
    position: relative;
    text-align: center;
}

nav a .logo {
    width: 250px;
}

.navbar .menu {
    position: relative;
    margin: 0 auto;
    padding: 0;
    z-index: 99;
}

.navbar .menu ul {
    margin: 0 auto;
    padding: 0;
}

.navbar .menu li {
    height: $menu-height;
    display: inline-block;
}

.navbar .menu > li > a {
    display: block;
    padding: 0 15px;
    height: $menu-height;
    line-height: $menu-height;
}

.dropdown-menu {
    position: absolute;
}

.navbar .menu .dropdown:hover .dropdown-menu li {
    display: block;
}

.navbar .menu .dropdown-menu li {
    display: none;
    text-align: left;
    height: $menu-dropdown-item-height;
    border-bottom: solid 1px;
    background: $menu-dropdown-color;
   
}

.navbar .menu .dropdown-menu li:last-child{
    border-bottom: none;
}

.navbar .menu .dropdown-menu li a {
    display: block;
    height: $menu-dropdown-item-height;
    line-height: $menu-dropdown-item-height;
    padding: 0 50px 0 15px;
}

.dropdown-icon::after {
    content: "";
}
"""
    newFiles(root / 'src/sass/_menu.scss', sassMenu)

    # _variables.scss
    sassVariables = """// Colors
$body-color: #eee;
$link-color: #000;
$menu-dropdown-color: #fff;

// Font
$body-font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;

// Menu
$menu-height: 30px;
$menu-dropdown-item-height: 40px;

// Content
$wrapper-width: 100%;
$container-width: 1000px;  
"""
    newFiles(root / 'src/sass/_variables.scss', sassVariables)

    # main.scss
    sassMain = """@import "variables.scss";
@import "setup.scss";
@import "menu.scss";

a {
    text-decoration: none;
    color: $link-color;
}
  
ul {
    list-style-type: none;
}

img {
    max-width: 100%;
    max-height: 100%;
}

#wrapper {
    width: $wrapper-width;
}

.container {
    width: $container-width;
    margin: 0 auto;
    padding: 10px;
}
"""
    newFiles(root / 'src/sass/main.scss', sassMain)


    # JavaScript file
    jsContent = "console.log('Javascript inicialized.');"
    newFiles(root / 'src/js/main.js', jsContent)


# Instala as dependências do composer e gulp
def dependencies(args):
    print('\n################################\n## Instalando as dependências ##\n################################\n')
    
    os.chdir(args.path / args.proj_dir / "wp-content" / "themes" / args.theme_dir)
    os.system('composer install;')
    os.system('ncu -u; npm install;')


# Inicia o Gulp
def gulp():
    os.system('gulp')


def new_wpconfig(args):
    # .env (arquivo de configuração)
    envContent = f"""# Environment configuration (development, production)
# IF development
#   Activate Debug messages

APP_ENV = development

###############################
# Database configuration
###############################

DB_HOST     = {args.db_host}
DB_NAME     = {args.wp_db_name}
DB_USER     = {args.db_user}
DB_PASSWORD = {args.db_passwd}
DB_PREFIX   = {args.wp_db_prefix}
DB_CHARSET  = {args.wp_db_charset}

###############################
# Site configuration
###############################

WP_HOME      = {args.urlBase + '/' + args.proj_dir}
WP_SITEURL   = {args.urlBase + '/' + args.proj_dir }
WP_DEBUG_LOG = true
FS_METHOD    = direct

###############################
# Post revisions
###############################

AUTOSAVE_INTERVAL = 5000
WP_POST_REVISIONS = 5

###############################
# Trash configuration
###############################

EMPTY_TRASH_DAYS = 7
"""
    newFiles(args.path / args.proj_dir / '.env', envContent)

    
    # wp-config.php
    # Substitui o wp-config gerado na instalação.
    wp_configKeys = os.popen('curl --silent https://api.wordpress.org/secret-key/1.1/salt/').read()
    wp_configContent = """<?php
/**
 * The base configuration for WordPress
 *
 * The wp-config.php creation script uses this file during the
 * installation. You don't have to use the web site, you can
 * copy this file to "wp-config.php" and fill in the values.
 *
 * This file contains the following configurations:
 *
 * * MySQL settings
 * * Secret keys
 * * Database table prefix
 * * ABSPATH
 *
 * @link https://codex.wordpress.org/Editing_wp-config.php
 *
 * @package WordPress
 */

/**
* Inclui a biblioteca Dotenv para carregar os valores do arquivo .env
*/
if ( file_exists( __DIR__ . '/wp-content/themes/%s/vendor/autoload.php' ) ):
    require_once __DIR__ . '/wp-content/themes/%s/vendor/autoload.php';
    $dotenv = new Dotenv\Dotenv( __DIR__ );
    $dotenv->load();
endif;

if ( file_exists( dirname( __DIR__ ) . '/wp-content/themes/%s/vendor/autoload.php' ) ):
    require_once dirname( __DIR__ ) . '/wp-content/themes/%s/vendor/autoload.php';
    $dotenv = new Dotenv\Dotenv( dirname( __DIR__ ) );
    $dotenv->load();
endif;


// ** MySQL settings ** //
/** The name of the database for WordPress */
define( 'DB_NAME', getenv( 'DB_NAME' ) );

/** MySQL database username */
define( 'DB_USER', getenv( 'DB_USER' ) );

/** MySQL database password */
define( 'DB_PASSWORD', getenv( 'DB_PASSWORD' ) );

/** MySQL hostname */
define( 'DB_HOST', getenv( 'DB_HOST' ) );

/** Database Charset to use in creating database tables. */
define( 'DB_CHARSET', getenv( 'DB_CHARSET' ) );

/** The Database Collate type. Don't change this if in doubt. */
define( 'DB_COLLATE', '' );

/**
 * Authentication Unique Keys and Salts.
 *
 * Change these to different unique phrases!
 * You can generate these using the {{@link https://api.wordpress.org/secret-key/1.1/salt/ WordPress.org secret-key service}}
 * You can change these at any point in time to invalidate all existing cookies. This will force all users to have to log in again.
 *
 * @since 2.6.0
 */

%s

/**
 * WordPress Database Table prefix.
 *
 * You can have multiple installations in one database if you give each
 * a unique prefix. Only numbers, letters, and underscores please!
 */
$table_prefix = getenv( 'DB_PREFIX' );

define( 'WP_DEBUG', getenv( 'APP_ENV' ) === 'development' ? true : false );
define( 'WP_DEBUG_LOG', getenv( 'WP_DEBUG_LOG' ) );
define( 'FS_METHOD', getenv( 'FS_METHOD' ) ); 

define( 'WP_HOME', getenv( 'WP_HOME' ) );
define( 'WP_SITEURL', getenv( 'WP_SITEURL' ));

define('AUTOSAVE_INTERVAL', getenv('AUTOSAVE_INTERVAL'));
define('WP_POST_REVISIONS', getenv('WP_POST_REVISIONS'));

define('EMPTY_TRASH_DAYS', getenv('EMPTY_TRASH_DAYS'));


/* That's all, stop editing! Happy blogging. */

/** Absolute path to the WordPress directory. */
if ( ! defined( 'ABSPATH' ) )
	define( 'ABSPATH', dirname( __FILE__ ) . '/' );

/** Sets up WordPress vars and included files. */
require_once ABSPATH . 'wp-settings.php';
""" % (args.theme_dir, args.theme_dir, args.theme_dir, args.theme_dir, wp_configKeys)
    newFiles(args.path / args.proj_dir / 'wp-config.php', wp_configContent)


# Instala lista de Plugins
def plugins():
    print('\n########################\n## Instalando Plugins ##\n########################\n')

    #pluginList = "advanced-custom-fields"
    pluginList = "advanced-custom-fields co-authors-plus contact-form-7 disqus-conditional-load mailchimp-for-wp multiple-post-thumbnails post-views-counter resize-image-after-upload wordpress-popular-posts tinymce-advanced wp-fastest-cache wp-job-manager wp-missed-schedule-posts wp-user-avatar yet-another-related-posts-plugin"
    os.system(f"wp plugin install {pluginList} --activate --path=$WPPATH --allow-root")


    
def main(args):
    print(args.install)
   
    prerequisites_met()

    create_database(args) 
    args.proj_dir = input('\nDiretório do projeto: ')
    args.theme_dir = input('\nDiretório do tema: ')
    
    args.wp_title = input('\nTítulo do site: ')
    args.wp_user_login = input('Login do usuário: ')
    args.wp_user_passwd = getpass('Senha do usuário: ')
    args.wp_user_email = input('Email do usuário: ')

    make_folders(args)
    download_wp(args)
    write_htaccess(args)
    configure_wp_core(args)
    create_wp_tables(args)
    cleanup_folders(args)
    add_template_files(args)
    final_wordpress_setup_steps(args)
    plugins()
    new_wpconfig(args)
    dependencies(args)
    menu_inicial()
    gulp()
    
    print("\n> Instalação concluída.")


if __name__ == "__main__":

    # Create argument parser
    parser = ArgumentParser(description=r"Script para instalar o Wordpress.")
    args = parser.parse_args()

    parser.add_argument("-ub", "--url_base", dest="urlBase", default="http://localhost")

    parser.add_argument("-i", "--install", dest="install", default="\n#################################\n  WordPress custom installation\n  Author: Fernando Goya\n  Version: 1.0\n  Website: www.fernandogoya.com\n#################################\n")
    parser.add_argument("-H", "--db_host", dest="db_host", help="Database host", default="127.0.0.1")
    parser.add_argument("-u", "--db_user", dest="db_user", help="Nome do usuário")
    parser.add_argument("-p", "--db_passwd", dest="db_passwd", help="Senha do usuário banco de dados")

    parser.add_argument("-P", "--path", dest="path", help="Diretório do projeto", default=server_path)
    
    parser.add_argument("-n", "--proj_dir", dest="proj_dir", help="Diretório do projeto")
    parser.add_argument("-th", "--theme_dir", dest="theme_dir", help="Diretório do tema")
 
    parser.add_argument("-d", "--wp_db_name", dest="wp_db_name", help="Nome do banco de dados")
    parser.add_argument("-v", "--wp_db_user", dest="wp_db_user", help="Wordpress Admin User/Nome do usuário")
    parser.add_argument("-w", "--wp_db_passwd", dest="wp_db_passwd", help="Wordpress Admin Password/Senha do usuário banco de dados")
    parser.add_argument("-px", "--wp_db_prefix", dest="wp_db_prefix", help="Prefixo da tabela", default='cwp_')
    parser.add_argument("-c", "--charset", dest="wp_db_charset", help="Database Charset", default='utf8')

    parser.add_argument("-t", "--wp_title", dest="wp_title", help="Titulo do site")
    parser.add_argument("-l", "--wp_user_login", dest="wp_user_login", help="Login de acesso")
    parser.add_argument("-k", "--wp_user_passwd", dest="wp_user_passwd", help="Senha de acesso")
    parser.add_argument("-e", "--wp_user_email", dest="wp_user_email", help="Email do usuário")


    args = parser.parse_args()

    main(args)

