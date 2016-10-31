<?xml version="1.0" encoding="UTF-8"?>

<!--
    xml2html.xsl - transform Bison XML Report into XHTML.

    Copyright (C) 2007, 2008, 2009, 2010 Free Software Foundation, Inc.

    This file is part of Bison, the GNU Compiler Compiler.

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

    Written by Wojciech Polak <polak@gnu.org>.
  -->

<xsl:stylesheet version="1.0"
  xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
  xmlns="http://www.w3.org/1999/xhtml"
  xmlns:bison="http://www.gnu.org/software/bison/">


<xsl:output method="xml" encoding="UTF-8"
	    doctype-public="-//W3C//DTD XHTML 1.0 Strict//EN"
	    doctype-system="http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd"
	    indent="yes"/>

<xsl:template match="/">
  <html>
    <head>
      <title>
		  <xsl:value-of select="WordInfo/@word"/>
      </title>
      <style type="text/css"><![CDATA[

		  @import url(https://fonts.googleapis.com/css?family=Droid+Serif:400,700,400italic,700italic);


		  /*============================*/
		  /*==== Master base style =====*/
		  /*============================*/
		  html, body {
			  font-family:'Droid Serif', serif;
			  font-weight:normal;
			  font-size: 14px;
			  padding: 0;
			  margin: 0;
			  color: #757474;
			  background: transparent;
		  }

		  /*============================*/
		  /*== highlight for anchor ====*/
		  /*============================*/
		  *[apple_anchor_highlight] {
			  background-color:#cbe6e6;
		  }

		  /*===============================*/
		  /*== highlight for mouseover ====*/
		  /*===============================*/
		  *[apple_mouseover_highlight]:hover {
			  color:#2971A7;
			  text-decoration:underline;
			  cursor:pointer;
		  }

		  *[apple_mouseover_highlight]:active {
			  color:#2971A7;
			  text-decoration:underline;
			  cursor:pointer;
		  }

		  /*===============================*/
		  /*== styles for definition ======*/
		  /*===============================*/
		  a:hover, a:visited, a:link {
			  color: #757474;
			  text-decoration: underline;
		  }
		  h1 {
			  position: fixed;
			  top: 0;
			  left: 0;
			  width: 100%;
			  z-index: 100;
			  display: block;
			  padding: 12px 18px 12px 18px;
			  color: #464646;
			  background: #F7F7F7;
			  border: 1px solid #E7E7E7;
			  border-top-width: 0;
			  border-left-width: 0;
			  border-right-width: 0;
			  font-size: 18px;
			  font-style: italic;
			  font-weight: 700;
			  margin: 0;
			  text-transform: capitalize;
		  }

		  ol {
		      counter-reset:li; /* Initiate a counter */
		      margin-left:0; /* Remove the default left margin */
		      padding-left:0; /* Remove the default left padding */
		  }
		  ol > li {
		      position:relative; /* Create a positioning context */
		      margin:0 0 6px 2em; /* Give each list item a left margin to make room for the numbers */
		      padding:4px 8px; /* Add some spacing around the content */
		      list-style:none; /* Disable the normal item numbering */
		  }
		  ol > li:before {
		      content:counter(li) "."; /* Use the counter as content */
		      counter-increment:li; /* Increment the counter by 1 */
		      /* Position and style the number */
		      position:absolute;
		      top:0;
		      left:-1.7em;
		      -moz-box-sizing:border-box;
		      -webkit-box-sizing:border-box;
		      box-sizing:border-box;
		      width:2em;
		      /* Some space between the number and the content in browsers that support
		         generated content but not positioning it (Camino 2 is one example) */
		      margin-right:4px;
		      padding:4px 0 4px 4px;
		      font-weight:bold;
			  font-size: bigger;
		      text-align:right;
		  }
		  li ol,
		  li ul {margin-top:6px;}
		  ol ol li:last-child {margin-bottom:0;}

		  #footer {
			  margin-top: 3.5em;
			  font-size: 7px;
		  }
		  span.label {
			  text-style: italic;
		  }
		  span.label:before {
			  content: "(";
		  }
		  span.label:after {
			  content: ")";
		  }
		  .ipa {
			  margin: 1em 3em;
		  }
		  .more {
			  margin: 1em 3em;
		  }
		  .more span {
			  font-weight: bold;
		  }
		  .scroll-body {
			  width: 100%;
			  height: 100%;
			  margin-top: 46px;
			  overflow-x: hidden;
			  overflow-y: auto;
		  }
		  parsererror {
			  display: none !important;
		  }
      ]]></style>
    </head>
    <body>
      <xsl:apply-templates select="WordInfo"/>
    </body>
  </html>
</xsl:template>

<xsl:template match="WordInfo">
	<h1><xsl:value-of select="@word" /></h1>
	<div class="scroll-body">
		<div class="ipa">
			<xsl:for-each select="ipa">
				<span><xsl:value-of select="." /></span>
			</xsl:for-each>
		</div>
		<ol>
			<xsl:for-each select="DictInfo/definition">
				<li><xsl:apply-templates select="." /></li>
			</xsl:for-each>
		</ol>
		<xsl:apply-templates select="TherInfo" />
		<xsl:apply-templates select="EtymologyInfo" />
		<!--<xsl:apply-templates select="LinkInfo" />-->
	</div>
</xsl:template>

<xsl:template match="definition">
	<div class="definition">
		<em><xsl:value-of select="@partOfSpeech"/>
			<xsl:text>:&#160;</xsl:text>
		</em>
		<xsl:value-of select="text()" disable-output-escaping="yes" />
		<ol>
			<xsl:for-each select="example">
				<li><xsl:apply-templates select="." /></li>
			</xsl:for-each>
		</ol>
	</div>
</xsl:template>

<xsl:template match="example">
	<div style="text-style: italic">
		<xsl:value-of select="." disable-output-escaping="yes" />
	</div>
</xsl:template>

<xsl:template match="LinkInfo">
	<div><a>
		<xsl:attribute name='href'><xsl:value-of select="@href" /></xsl:attribute>
		<xsl:attribute name='title'><xsl:value-of select="@title" /></xsl:attribute>
		<xsl:value-of select="@title" /></a>
	</div>
</xsl:template>

<xsl:template match="EtymologyInfo">
	<div class="more"><span>Origin:&#160;</span><xsl:value-of select="."
	disable-output-escaping="yes" /></div>
</xsl:template>

<xsl:template match="TherInfo">
	<div class="more"><span>Synonyms:&#160;</span>
	<xsl:for-each select="synonym">
		<xsl:value-of select="." />
	</xsl:for-each>
	</div>
</xsl:template>

<!--
<xsl:template match="strong">
	<strong><xsl:apply-templates /></strong>
</xsl:template>

<xsl:template match="em">
	<em><xsl:apply-templates /></em>
</xsl:template>


  <xsl:text>&#10;&#10;</xsl:text>
  <h3>Table of Contents</h3>
  <ul id="menu">
    <li>
      <a href="#reductions">Reductions</a>
      <ul class="lower-alpha">
	<li><a href="#nonterminals_useless_in_grammar">Nonterminals useless in grammar</a></li>
	<li><a href="#terminals_unused_in_grammar">Terminals unused in grammar</a></li>
	<li><a href="#rules_useless_in_grammar">Rules useless in grammar</a></li>
	<xsl:if test="grammar/rules/rule[@usefulness='useless-in-parser']">
	  <li><a href="#rules_useless_in_parser">Rules useless in parser due to conflicts</a></li>
	</xsl:if>
      </ul>
    </li>
    <li><a href="#conflicts">Conflicts</a></li>
    <li>
      <a href="#grammar">Grammar</a>
      <ul class="lower-alpha">
	<li><a href="#grammar">Itemset</a></li>
	<li><a href="#terminals">Terminal symbols</a></li>
	<li><a href="#nonterminals">Nonterminal symbols</a></li>
      </ul>
    </li>
    <li><a href="#automaton">Automaton</a></li>
  </ul>
  <xsl:apply-templates select="grammar" mode="reductions"/>
  <xsl:apply-templates select="grammar" mode="useless-in-parser"/>
  <xsl:apply-templates select="automaton" mode="conflicts"/>
  <xsl:apply-templates select="grammar"/>
  <xsl:apply-templates select="automaton"/>
</xsl:template>
-->

</xsl:stylesheet>
