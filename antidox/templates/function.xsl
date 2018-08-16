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
                <xsl:attribute name="ids"><xsl:value-of select="@id"/></xsl:attribute>
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
            </desc_signature>
            <desc_content>
                <xsl:apply-templates select="initializer"/>
                <xsl:apply-templates select="detaileddescription"/>
            </desc_content>
        </desc>
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

    <xsl:template match="declname|defname">
        <xsl:text> </xsl:text><emphasis><xsl:value-of select="."/></emphasis>
    </xsl:template>

    <xsl:template match="para">
        <paragraph><xsl:apply-templates /></paragraph>
    </xsl:template>
    <xsl:template match="para/para">
        <xsl:apply-templates />
    </xsl:template>
    <xsl:template match="para/text()">
        <xsl:copy/>
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

    <xsl:template match="simplesect"/>

    <xsl:template match="initializer">
        <antidox:directive antidox:name="code-block" linenos="">
        <antidox:directive-argument>c</antidox:directive-argument>
        <antidox:directive-content><xsl:value-of select="." /></antidox:directive-content>
        </antidox:directive>
    </xsl:template>

    <!-- This prevents whitespace from polluting the output
         Without this template, text nodes end up as children of elements that
         do not expect text as children (e.g <field>)
    -->
    <xsl:template match="text()" />
    <xsl:template match="type/text()"><xsl:copy/></xsl:template>

</xsl:stylesheet>
