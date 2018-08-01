<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" version="1.0">
  <xsl:output method="xml" indent="yes"/>

    <xsl:template match="/memberdef[@kind='function']">
      <desc desctype="function" domain="c" noindex="False" objtype="function">
        <desc_signature first="False">
        <xsl:attribute name="ids"><xsl:value-of select="@id"/></xsl:attribute>
        <xsl:attribute name="names"><xsl:value-of select="name"/></xsl:attribute>
        <desc_type><xsl:value-of select="type" /></desc_type>
        <desc_name> <xsl:value-of select="name" /></desc_name>
        <desc_parameterlist>
          <xsl:for-each select="param">
            <desc_parameter noemph="True">
                <xsl:apply-templates/>
            </desc_parameter>
          </xsl:for-each>
        </desc_parameterlist>
        </desc_signature>
        <desc_content>

        </desc_content>
      </desc>
    </xsl:template>

    <xsl:template match="/memberdef[@kind='typedef']">
      <desc desctype="type" domain="c" noindex="False" objtype="type">
        <desc_type><xsl:value-of select="type" /></desc_type>
        <desc_name> <xsl:value-of select="name" /></desc_name>
      </desc>
    </xsl:template>

    <xsl:template match="//ref">
        <pending_xref refdomain='c' reftype='any'>
        <xsl:attribute name="reftarget"><xsl:value-of select="@refid"/></xsl:attribute>
        <xsl:value-of select="."/>
        </pending_xref>
    </xsl:template>

    <xsl:template match="//declname">
        <emphasis><xsl:value-of select="."/></emphasis>
    </xsl:template>

    <xsl:template match='//para'>
        <compound><xsl:value-of select="."/></compound>
    </xsl:template>

    <xsl:template match='//parameterlist'>
        <compound><xsl:value-of select="."/></compound>
    </xsl:template>



</xsl:stylesheet>
