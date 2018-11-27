<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
                xmlns:antidox="antidox"
                version="1.0">
    <xsl:output method="xml" indent="yes"/>

    <xsl:template match="/memberdef[@kind='function']">
        <xsl:call-template name="memberdef-internal">
            <xsl:with-param name="role">function</xsl:with-param>
        </xsl:call-template>
    </xsl:template>

    <xsl:template match="/memberdef[@kind='typedef']">
        <xsl:call-template name="memberdef-internal">
            <xsl:with-param name="role">type</xsl:with-param>
        </xsl:call-template>
    </xsl:template>

    <xsl:template match="/memberdef[@kind='define']">
        <xsl:call-template name="memberdef-internal">
            <xsl:with-param name="role">macro</xsl:with-param>
        </xsl:call-template>
    </xsl:template>

    <xsl:template name="memberdef-internal">
        <xsl:param name = "role" />
        <desc domain="c" noindex="False">
            <xsl:attribute name="desctype"><xsl:value-of select="$role"/></xsl:attribute>
            <xsl:attribute name="objtype"><xsl:value-of select="$role"/></xsl:attribute>
            <desc_signature first="False">
                <xsl:attribute name="ids">c.<xsl:value-of select="@id"/></xsl:attribute>
                <xsl:attribute name="names"><xsl:value-of select="name"/></xsl:attribute>
                <xsl:apply-templates select="type|name"/>
                <xsl:if test="argsstring/text()|param">
                <desc_parameterlist>
                  <xsl:for-each select="param">
                    <desc_parameter noemph="True">
                        <xsl:apply-templates/>
                    </desc_parameter>
                  </xsl:for-each>
                </desc_parameterlist>
                </xsl:if>
                <antidox:index/>
            </desc_signature>
            <desc_content>
                <xsl:apply-templates select="initializer"/>
                <xsl:apply-templates select="detaileddescription"/>
            </desc_content>
        </desc>
    </xsl:template>

    <xsl:template match="/memberdef[@kind='enum']">
        <desc domain="c" noindex="False">
            <xsl:attribute name="desctype"><xsl:value-of select="type"/></xsl:attribute>
            <xsl:attribute name="objtype"><xsl:value-of select="type"/></xsl:attribute>
            <desc_signature first="False">
                <xsl:attribute name="ids">c.<xsl:value-of select="@id"/></xsl:attribute>
                <xsl:attribute name="names"><xsl:value-of select="name"/></xsl:attribute>
                <desc_type><xsl:text>enum</xsl:text></desc_type>
                <xsl:apply-templates select="name"/>
                <antidox:index/>
            </desc_signature>
            <desc_content>
            <definition_list>
                <xsl:for-each select="enumvalue">
                    <definition_list_item objtype="value">
                        <xsl:attribute name="ids">c.<xsl:value-of select="@id"/></xsl:attribute>
                        <xsl:attribute name="names"><xsl:value-of select="name"/></xsl:attribute>
                        <term><xsl:value-of select="name"/><xsl:apply-templates select="initializer"/></term>
                        <definition><xsl:apply-templates select="briefdescription|detaileddescription"/></definition>
                        <antidox:index/>
                    </definition_list_item>
                </xsl:for-each>
            </definition_list>
            </desc_content>
        </desc>
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
    <!-- avoid leaving text elements floating around outside a paragraph.
         The XSD does not specify this, but from what I've seen if a <para>
         starts with text (or ref) it should be OK to enclose it in <paragraph>
    <xsl:template match="detaileddescription/para[child::text()[normalize-space(text()) != '']]">
        <paragraph><xsl:apply-templates/></paragraph>
    </xsl:template>-->

    <!--Small workaround for groups without @brief -->
    <xsl:template match="/compounddef"/>

    <xsl:template match="/compounddef[briefdescription//text()]">
        <section>
        <xsl:attribute name="ids">c.<xsl:value-of select="@id"/></xsl:attribute>
        <title><xsl:apply-templates select="briefdescription"/></title>
        <!-- Catch all that is outside a heading -->
        <xsl:apply-templates select="detaileddescription/para[not(text()[normalize-space()])]/child::*[not(preceding::heading or self::heading)]|
                                     detaileddescription/para[text()[normalize-space()] and not(preceding::heading or self::heading)]"/>
        <xsl:apply-templates select="detaileddescription/para/heading[@level=1]"/>
        </section>
    </xsl:template>

    <!-- doxygen does not encapsulate a header and it's content in a container,
    instead it just intercalates both. See the following post to understand
    what we are doing here:
    https://stackoverflow.com/questions/2165566/xslt-select-following-sibling-until-reaching-a-specified-tag
    This one is a bit more complex because headers can be nested.
    There are three types if content included by this <apply-template/> below:
    1. Include simple paragraphs that contain only text, but only if they are immediately preceded by this section heading
    1.1. Like 1, but for paragraphs without text, dissolve them (include children directly). This has to be done
         here because a section can be broken in the middle of a <para> (doxy-weirdness).
    2. Include all headings exactly one level below this one (and preceded by this one)

    The important thing is that in (1) and (1.1) the test is done against heading of all
    levels, while the comparison in (2) is only with headings at the current level.
    -->
    <xsl:template match="detaileddescription/para/heading">
        <xsl:variable name="heading" select="generate-id(.)"/>
        <xsl:variable name="level" select="number(@level)"/>
        <section> <!-- TODO: add section ID (how do we handle duplicates?) -->
            <xsl:attribute name="ids">c.<xsl:value-of select="ancestor::*/@id"/>-<xsl:call-template name="string-to-ids"/></xsl:attribute>
            <!-- Small workaround for trailing whitespace in titles -->
            <title><xsl:value-of select="normalize-space(.)"/></title>
            <xsl:apply-templates
select="parent::*/following-sibling::para[(ref or text()[normalize-space()]) and generate-id(preceding::heading[1])=$heading]|
parent::*/following-sibling::para[not(ref or text()[normalize-space()])]/*[not(self::heading) and generate-id(preceding::heading[1])=$heading]|
parent::*/following-sibling::*/heading[number(@level)=($level+1) and generate-id(preceding::heading[$level=number(@level)][1])=$heading]"/>
        </section>
    </xsl:template>

    <xsl:template match="type">
        <desc_type><xsl:apply-templates/></desc_type>
    </xsl:template>

    <xsl:template match="memberdef/name">
        <desc_name><xsl:text> </xsl:text><xsl:value-of select="." /></desc_name>
    </xsl:template>

    <xsl:template match="//ref">
        <pending_xref refdomain='c' reftype='any'>
        <xsl:attribute name="reftarget"><xsl:value-of select="@refid"/></xsl:attribute>
        <xsl:value-of select="."/>
        </pending_xref>
    </xsl:template>

    <xsl:template match="orderedlist">
        <enumerated_list enumtype="arabic" prefix="" suffix=".">
        <xsl:for-each select="listitem">
            <list_item><xsl:apply-templates/></list_item>
        </xsl:for-each>
        </enumerated_list>
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

    <!-- TODO: provide special case for RFC urls using the :rfc: role -->

    <xsl:template match="para">
        <paragraph><xsl:apply-templates /></paragraph>
    </xsl:template>
    <xsl:template match="para/para|briefdescription/para">
        <xsl:apply-templates />
    </xsl:template>

    <!-- normal processiong for briefdescription, just go inside -->
    <xsl:template match="briefdescription">
        <xsl:apply-templates />
    </xsl:template>

    <!-- if the briefdescription is a title, then dissolve paragraphs -->
    <xsl:template match="compounddef/briefdescription/para">
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
        <rubric><xsl:text antidox:l="true">Parameters</xsl:text></rubric>
        <field_list>
            <xsl:apply-templates/>
        </field_list>
    </xsl:template>

    <xsl:template match="detaileddescription">
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
        <antidox:directive antidox:name="code-block" linenos="">
        <antidox:directive-argument>c</antidox:directive-argument>
        <antidox:directive-content><xsl:value-of select="." /></antidox:directive-content>
        </antidox:directive>
    </xsl:template>

    <xsl:template name="string-to-ids"><xsl:value-of select="
          translate(
            translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ ', 'abcdefghijklmnopqrstuvwxyz-'),
            translate(
              .,
              'abcdefghijklmnopqrstuvwxyz0123456789-_',
              ''
            ),
            ''
          )" /></xsl:template>

    <!-- This prevents whitespace from polluting the output
         Without this template, text nodes end up as children of elements that
         do not expect text as children (e.g <field>)
    -->
    <xsl:template match="text()" />
    <xsl:template match="type/text()"><xsl:copy/></xsl:template>

</xsl:stylesheet>
