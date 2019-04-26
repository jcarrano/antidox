<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
                xmlns:antidox="antidox"
                version="1.0">
    <xsl:output method="xml" indent="yes"/>

    <!-- Global parameters. These are received from the directive options. -->

    <xsl:param name="noindex" select="false()"/>
    <xsl:param name="hideloc" select="false()"/>
    <xsl:param name="hidedef" select="false()"/>
    <xsl:param name="hidedoc" select="false()"/>

    <xsl:template match="/memberdef">
        <xsl:param name="role" select="antidox:guess_desctype(@id)"/>
        <desc domain="c">
            <xsl:attribute name="noindex"><xsl:value-of select="$noindex"/></xsl:attribute>
            <xsl:attribute name="desctype"><xsl:value-of select="$role"/></xsl:attribute>
            <xsl:attribute name="objtype"><xsl:value-of select="$role"/></xsl:attribute>
            <desc_signature first="false">
                <xsl:attribute name="ids">c.<xsl:value-of select="@id"/></xsl:attribute>
                <xsl:attribute name="names"><xsl:value-of select="antidox:refid_to_target(@id)"/></xsl:attribute>
                <xsl:apply-templates select="type|name"/>
                <xsl:if test="argsstring/text()|param">
                <desc_parameterlist>
                  <xsl:for-each select="param">
                    <desc_parameter noemph="true">
                        <xsl:apply-templates/>
                    </desc_parameter>
                  </xsl:for-each>
                </desc_parameterlist>
                </xsl:if>
                <xsl:call-template name="keyed-index"/>
            </desc_signature>
            <xsl:if test="not($hidedoc)">
                <desc_content>
                    <xsl:apply-templates select="briefdescription"/>
                    <xsl:apply-templates select="initializer"/>
                    <xsl:apply-templates select="detaileddescription"/>
                </desc_content>
            </xsl:if>
        </desc>
    </xsl:template>

    <xsl:template match="/memberdef[@kind='enum']">
        <xsl:param name="enumname" select="name"/>
        <desc domain="c">
            <xsl:attribute name="noindex"><xsl:value-of select="$noindex"/></xsl:attribute>
            <xsl:attribute name="desctype">type</xsl:attribute>
            <xsl:attribute name="objtype">type</xsl:attribute>
            <desc_signature first="False">
                <xsl:attribute name="ids">c.<xsl:value-of select="@id"/></xsl:attribute>
                <xsl:attribute name="names"><xsl:value-of select="antidox:refid_to_target(@id)"/></xsl:attribute>
                <desc_type><xsl:text>enum</xsl:text></desc_type>
                <xsl:apply-templates select="name"/>
                <xsl:call-template name="keyed-index"/>
            </desc_signature>
            <xsl:if test="not($hidedoc)">
            <desc_content>
            <definition_list>
                <antidox:children/>
            </definition_list>
            </desc_content>
            </xsl:if>
        </desc>
    </xsl:template>

    <!-- FIXME: this will catch fire if someone tries to include an enumvalue
         outside an enum!!! -->
    <xsl:template match="/enumvalue">
        <definition_list_item objtype="value">
            <xsl:attribute name="ids">c.<xsl:value-of select="@id"/></xsl:attribute>
            <!-- This causes repeated ids
            <xsl:attribute name="names"><xsl:value-of select="@id"/></xsl:attribute>
            -->
            <term><xsl:value-of select="name"/><xsl:apply-templates select="initializer"/></term>
            <definition><xsl:apply-templates select="briefdescription|detaileddescription"/></definition>
            <xsl:call-template name="keyed-index">
                <!-- FIXME: restore "$enumname" -->
                <xsl:with-param name="key-word"><xsl:value-of select="name"/></xsl:with-param>
            </xsl:call-template>
        </definition_list_item>
    </xsl:template>

    <!-- Create an index entry using the first letter of "key-word" (by default
         the key-word is taken from the <name> element) -->
    <xsl:template name="keyed-index">
        <xsl:param name="key-word" select="name"/>
        <xsl:if test="not($noindex)">
            <antidox:index>
                <xsl:attribute name="key"><xsl:value-of select="antidox:upper-case(substring($key-word, 1, 1))"/></xsl:attribute>
            </antidox:index>
        </xsl:if>
    </xsl:template>

    <xsl:template match="enumvalue/initializer">
        <xsl:text> </xsl:text><antidox:interpreted role="code"><xsl:value-of select="."/></antidox:interpreted>
    </xsl:template>

    <!-- detailed descriptions are full of <para> for no reason, dissolve them
    <xsl:template match="/doxygen/compounddef/detaileddescription/para">
        <xsl:apply-templates/>
    </xsl:template>

    <xsl:template match="/doxygen/compounddef/detaileddescription/para[text()]">
        <paragraph><xsl:apply-templates/></paragraph>
    </xsl:template>
-->
    <!--
         The XSD does not specify this, but from what I've seen if a <para>
         starts with text (or ref) it should be OK to enclose it in <paragraph>
    <xsl:template match="detaileddescription/para[child::text()[normalize-space(text()) != '']]">
        <paragraph><xsl:apply-templates/></paragraph>
    </xsl:template>-->

    <!--Small workaround for groups without @brief -->
    <xsl:template match="/compounddef"/>

    <xsl:template match="/compounddef[(briefdescription//text() and (@kind = 'group' or @kind = 'file')) or @kind = 'page']">
    <!-- see https://stackoverflow.com/questions/1128745/how-can-i-use-xpath-to-find-the-minimum-value-of-an-attribute-in-a-set-of-elemen -->
        <xsl:variable name="minlevel" select="detaileddescription/para/heading/@level[not(. > ../../../heading/@level)][1]"/>
        <section>
        <xsl:attribute name="ids">c.<xsl:value-of select="@id"/></xsl:attribute>
        <xsl:attribute name="names"><xsl:value-of select="@id"/>|<xsl:value-of select="compoundname"/>[<xsl:value-of select="@kind"/>]</xsl:attribute>
        <xsl:apply-templates select="title|compoundname"/>
        <subtitle><xsl:apply-templates select="briefdescription"/></subtitle>
        <!-- Catch all that is outside a heading -->
        <xsl:if test="not($hidedoc)">
        <!-- See below for an explanation of why we dissolve paragraphs with headings -->
        <xsl:apply-templates select="detaileddescription/para[descendant::heading]/child::*[not(preceding::heading or self::heading)]|
                                     detaileddescription/para[not(preceding::heading or descendant::heading)]"/>
        <xsl:apply-templates select="detaileddescription/para/heading[@level=$minlevel]|detaileddescription/sect1|detaileddescription/sect2"/>
        </xsl:if>
        </section>
    </xsl:template>

    <xsl:template match="/compounddef/title">
        <title><xsl:apply-templates/></title>
    </xsl:template>

    <xsl:template match="/compounddef[not(title)]/compoundname/text()">
        <title><xsl:copy/></title>
    </xsl:template>

    <xsl:template match="/compounddef[@kind = 'struct' or @kind = 'union']">
        <desc domain="c" desctype="type" objtype="type">
            <xsl:attribute name="noindex"><xsl:value-of select="$noindex"/></xsl:attribute>
            <desc_signature first="false">
                <xsl:attribute name="ids">c.<xsl:value-of select="@id"/></xsl:attribute>
                <xsl:attribute name="names"><xsl:value-of select="compoundname"/></xsl:attribute>
                <desc_type><xsl:value-of select="@kind"/></desc_type>
                <desc_name><xsl:text> </xsl:text><xsl:value-of select="compoundname" /></desc_name>
                <xsl:if test="not($noindex)"><antidox:index/></xsl:if>
            </desc_signature>
            <xsl:if test="not($hidedoc)">
                <desc_content>
                    <xsl:apply-templates select="briefdescription"/>
                    <xsl:apply-templates select="detaileddescription"/>
                    <antidox:children/>
                </desc_content>
            </xsl:if>
        </desc>
    </xsl:template>

    <xsl:template match="detaileddescription/sect1|detaileddescription/sect2">
        <xsl:variable name="minlevel" select="detaileddescription/para/heading/@level[not(. > ../../../heading/@level)][1]"/>
        <section>
        <xsl:attribute name="ids"><xsl:value-of select="@id"/></xsl:attribute>
        <title><xsl:apply-templates select="title/text()"/></title>
        <xsl:apply-templates select="para[not(preceding::heading or descendant::heading)]|
                                     para[descendant::heading]/child::*[not(preceding::heading or self::heading)]"/>
        <xsl:apply-templates select="para/heading[@level=$minlevel]|sect1|sect2"/>
        </section>
    </xsl:template>

    <!-- doxygen does not encapsulate a header and its content in a container,
    instead it just intercalates both. See the following post to understand
    what we are doing here:
    https://stackoverflow.com/questions/2165566/xslt-select-following-sibling-until-reaching-a-specified-tag
    This one is a bit more complex because headers can be nested.
    There are three types if content included by this <apply-template/> below:

    1. Paragraphs that don't contain headers are included directly.
    1.1. Sections can be broken in the middle of a <para> (doxy-weirdness), so
         paragraphs containing any type of header are dissolved. Here we are hoping
         that if it contains a header, then it should be safe to dissolve it.
    2. Include all headings exactly one level below this one (and preceded by this one)

    The important thing is that in (1) and (1.1) the test is done against heading of all
    levels, while the comparison in (2) is only with headings at the current level.
    -->
    <xsl:template match="detaileddescription/para/heading|sect1/para/heading">
        <xsl:variable name="heading" select="generate-id(.)"/>
        <xsl:variable name="level" select="number(@level)"/>
        <!-- TODO: add section ID (how do we handle duplicates?) -->
        <xsl:if test="not($hidedoc)">
        <section>
            <xsl:attribute name="ids"><xsl:value-of select="concat('c.',ancestor::*/@id,'-',antidox:string-to-ids(.))"/></xsl:attribute>
            <!-- Small workaround for trailing whitespace in titles -->
            <title><xsl:value-of select="normalize-space(.)"/></title>
            <xsl:apply-templates
select="parent::*/following-sibling::para[not(descendant::heading) and generate-id(preceding::heading[1])=$heading]" />
            <paragraph>
            <xsl:apply-templates
select="parent::*/following-sibling::para[descendant::heading]/*[not(self::heading) and generate-id(preceding::heading[1])=$heading]"/>
            </paragraph>
            <xsl:apply-templates
select="parent::*/following-sibling::*/heading[number(@level)=($level+1) and generate-id(preceding::heading[$level=number(@level)][1])=$heading]"/>
        </section>
        </xsl:if>
    </xsl:template>

    <!-- Prevents losing lose text when applying rule 1.1 described above. -->

    <xsl:template match="type">
        <desc_type><xsl:apply-templates/></desc_type>
    </xsl:template>

    <xsl:template match="memberdef/name">
        <desc_name><xsl:text> </xsl:text><xsl:value-of select="." /></desc_name>
    </xsl:template>

    <!-- Using doxy:r here instead of directly inserting a pending_xref allows
         more robust handling of the different kind of references in doxygen. -->
    <!-- TODO: figure out how to put hyperlinks in program listings. -->
    <xsl:template match="ref[not(ancestor::programlisting)]">
        <!-- FIXME: some compounds should be not be given explicit titles. Maybe
             no reference should be given a explicit title??? -->
        <antidox:interpreted role="doxy:r">
        <xsl:if test="@kindref!='member'"><xsl:value-of select="."/><xsl:text> &lt;</xsl:text></xsl:if>
        !<xsl:value-of select="@refid"/><xsl:if test="@kindref!='member'"><xsl:text>&gt;</xsl:text></xsl:if>
        </antidox:interpreted>
    </xsl:template>

    <xsl:template match="ref[ancestor::programlisting]">
        <xsl:value-of select="."/>
    </xsl:template>

    <xsl:template match="orderedlist">
        <enumerated_list enumtype="arabic" prefix="" suffix=".">
            <xsl:apply-templates/>
        </enumerated_list>
    </xsl:template>

    <xsl:template match="itemizedlist">
        <bullet_list bullet="-">
            <xsl:apply-templates/>
        </bullet_list>
    </xsl:template>

    <xsl:template match="listitem">
        <list_item><xsl:apply-templates/></list_item>
    </xsl:template>

    <!-- This is probably incomplete -->
    <xsl:template match="table">
        <table>
            <tgroup>
            <xsl:attribute name="cols"><xsl:value-of select="@cols"/></xsl:attribute>
                <xsl:apply-templates mode="colspec" select="row/entry[@thead='yes']"/>
                <thead><xsl:apply-templates select="row[entry[@thead='yes']]"/></thead>
                <tbody><xsl:apply-templates select="row[entry[@thead='no']]"/></tbody>
            </tgroup>
        </table>
    </xsl:template>

    <xsl:template match="*" mode="colspec">
        <colspec colwidth="1"/>
    </xsl:template>

    <xsl:template match="row|entry">
        <xsl:copy><xsl:apply-templates/></xsl:copy>
    </xsl:template>

    <xsl:template match="bold"><strong><xsl:apply-templates/></strong></xsl:template>

    <xsl:template match="emphasis"><emphasis><xsl:apply-templates/></emphasis></xsl:template>

    <xsl:template match="computeroutput">
        <literal><xsl:value-of select="."/></literal>
    </xsl:template>

    <xsl:template match="programlisting">
        <antidox:directive antidox:name="code-block" linenos="">
        <antidox:directive-argument>c</antidox:directive-argument>
        <antidox:directive-content><xsl:apply-templates/></antidox:directive-content>
        </antidox:directive>
    </xsl:template>

    <xsl:template match="codeline"><xsl:apply-templates/>
<xsl:text>
</xsl:text><!-- this newline is the key -->
    </xsl:template>

    <xsl:template match="codeline/highlight/text()"><xsl:value-of select="normalize-space(.)"/></xsl:template>
    <xsl:template match="codeline/highlight/sp"><xsl:text> </xsl:text></xsl:template>

    <xsl:template match="declname|defname">
        <xsl:text> </xsl:text><emphasis><xsl:value-of select="."/></emphasis>
    </xsl:template>

    <xsl:template match="ulink">
        <reference>
            <xsl:attribute name="name"><xsl:value-of select="."/></xsl:attribute>
            <xsl:attribute name="refuri"><xsl:value-of select="@url"/></xsl:attribute>
            <xsl:value-of select="."/>
        </reference>
    </xsl:template>

    <!-- Special case for RFC urls using the :rfc: role  -->
    <xsl:template match="ulink[starts-with(@url, 'http://tools.ietf.org/html/rfc')]">
        <xsl:variable name="rfc_n_sect" select="substring-after(@url, 'http://tools.ietf.org/html/rfc')"/>
        <antidox:interpreted role="rfc"><xsl:value-of select="."/><xsl:text> &lt;</xsl:text><xsl:value-of select="$rfc_n_sect"/><xsl:text>&gt;</xsl:text></antidox:interpreted>
    </xsl:template>

    <xsl:template match="para">
        <paragraph><xsl:apply-templates /></paragraph>
    </xsl:template>

    <!-- Dissolve nested paragraphs -->
    <xsl:template match="para/para">
        <xsl:apply-templates />
    </xsl:template>

    <!-- normal processiong for briefdescription, just go inside (i.e. dissolve) -->
    <xsl:template match="briefdescription">
        <xsl:apply-templates />
    </xsl:template>

    <!-- if the briefdescription is a title, then dissolve paragraphs, but only
         for entities that we render with titles (files and group) -->
    <xsl:template match="compounddef[@kind = 'group' or @kind = 'file']/briefdescription/para">
        <xsl:apply-templates />
    </xsl:template>

    <xsl:template match="parameteritem">
        <field>
            <field_name>
                <xsl:apply-templates select="parameternamelist"/>
            </field_name>
            <field_body>
                <xsl:apply-templates select="parameterdescription"/>
            </field_body>
        </field>
    </xsl:template>

    <xsl:template match="parametername">
        <xsl:value-of select="."/>
        <xsl:if test="following-sibling::*"><xsl:text>, </xsl:text></xsl:if>
    </xsl:template>

    <xsl:template match='parameterlist'>
        <rubric><xsl:value-of select="antidox:l('Parameters')"/></rubric>
        <field_list>
            <xsl:apply-templates/>
        </field_list>
    </xsl:template>

    <xsl:template match="memberdef/detaileddescription">
        <xsl:apply-templates/>
        <xsl:if test="descendant::simplesect[@kind='return']">
            <rubric><xsl:text>Return values</xsl:text></rubric>
            <bullet_list>
                <xsl:for-each select="descendant::simplesect[@kind='return']">
                <list_item><xsl:apply-templates/></list_item>
                </xsl:for-each>
            </bullet_list>
        </xsl:if>
    </xsl:template>

    <!-- Kill simplesects by default -->
    <xsl:template match="simplesect"/>

    <xsl:template match="simplesect[@kind='note']">
    <note><xsl:apply-templates/></note>
    </xsl:template>

    <xsl:template match="simplesect[@kind='see']">
    <seealso><xsl:apply-templates/></seealso>
    </xsl:template>

    <xsl:template match="initializer">
        <xsl:if test="not($hidedef)">
        <antidox:directive antidox:name="code-block" linenos="">
        <antidox:directive-argument>c</antidox:directive-argument>
        <antidox:directive-content><xsl:value-of select="." /></antidox:directive-content>
        </antidox:directive>
        </xsl:if>
    </xsl:template>

    <!-- This prevents whitespace from polluting the output
         Without this template, text nodes end up as children of elements that
         do not expect text as children (e.g <field>)
    -->
    <xsl:template match="text()" />

    <!-- these are the only elements allowed to produce text -->
    <xsl:template match="para/text()|bold/text()|emphasis/text()|type/text()|title/text()"><xsl:copy/></xsl:template>

</xsl:stylesheet>
