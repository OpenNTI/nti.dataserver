#!/bin/bash
set -e
ENV=~/tmp/AlphaExport

nti_create_user $ENV nathan.fite@ou.edu nathan.fite --name "Nathan Fite"
nti_create_user $ENV Kevin.M.Finson-1@ou.edu kevin.finson --name "Kevin Finson"
nti_create_user $ENV katherineobrien@ou.edu katherine.obrien --name "Katherine O'Brien"
nti_create_user $ENV bchurchman@ou.edu brooke.churchman --name "Brooke Churchman"
nti_create_user $ENV andrewscribner@ou.edu andrew.scribner --name "Andrew Scribner"
nti_create_user $ENV iosteen@uoregon.edu ian.osteen --name "Ian Osteen"
nti_create_user $ENV Aaron.C.Brooks-1@ou.edu aaran.brooks --name "Aaron Brooks"

nti_create_user $ENV Oxford --type provider

nti_create_class $ENV Oxford 6100 --name "Free Speech" --section-id 604 -i thai@post.harvard.edu stephen.henderson@aya.yale.edu \
 --enrolled nathan.fite@ou.edu Kevin.M.Finson-1@ou.edu katherineobrien@ou.edu bchurchman@ou.edu andrewscribner@ou.edu iosteen@uoregon.edu Aaron.C.Brooks-1@ou.edu greg.higgins@nextthought.com jason.madden@nextthought.com sean.jones@nextthought.com
