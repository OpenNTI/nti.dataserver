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
/*============================*/
/*==== Master base style =====*/
/*============================*/
body {
	font-family:'Baskerville';
	font-weight:normal;
	font-size: medium;
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
/*	border-bottom-style:dotted;
	border-bottom-width:1px;
	border-bottom-color:#0000ff;*/
	cursor:pointer;
}

*[apple_mouseover_highlight]:active {
	color:#2971A7;
	text-decoration:underline;
/*	border-bottom-style:dotted;
	border-bottom-width:1px;
	border-bottom-color:#ff0000;*/
	cursor:pointer;
}
      body {
        font-family: "Nimbus Sans L", Arial, sans-serif;
	font-size: 9pt;
      }
      a:link {
 	color: #1f00ff;
	text-decoration: none;
      }
      a:visited {
 	color: #1f00ff;
	text-decoration: none;
      }
      a:hover {
 	color: red;
      }
      #menu a {
        text-decoration: underline;
      }
      .i {
        font-style: italic;
      }
      .pre {
        font-family: monospace;
        white-space: pre;
      }
      ol.decimal {
        list-style-type: decimal;
      }
      ol.lower-alpha {
        list-style-type: lower-alpha;
      }
      .point {
        color: #cc0000;
      }
      #footer {
        margin-top: 3.5em;
        font-size: 7pt;
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
	<xsl:for-each select="ipa">
		<span style="text-style: bold"><xsl:value-of select="." /></span>
	</xsl:for-each>
	<ol>
		<xsl:for-each select="DictInfo/definition">
			<li><xsl:apply-templates select="." /></li>
		</xsl:for-each>
	</ol>
	<xsl:apply-templates select="TherInfo" />
	<xsl:apply-templates select="EtymologyInfo" />
	<xsl:apply-templates select="LinkInfo" />
</xsl:template>

<xsl:template match="definition">
	<em><xsl:value-of select="@partOfSpeech"/></em>
	<xsl:text>&#160;</xsl:text>
	<xsl:value-of select="text()" disable-output-escaping="yes" />
	<ol>
		<xsl:for-each select="example">
			<li><xsl:apply-templates select="." /></li>
		</xsl:for-each>
	</ol>
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
	<div><span>Origin&#160;</span><xsl:value-of select="."
	disable-output-escaping="yes" /></div>
</xsl:template>

<xsl:template match="TherInfo">
	<div>Synonyms&#160;
	<xsl:for-each select="synonym">
		<xsl:value-of select="." />&#160;
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
