"""
    antidox.directives
    ~~~~~~~~~~~~~~~~~~

    C domain directives for documenting Doxygen elements. These directives try
    to take advantage of the work done by Doxygen to avoid having to parse C
    source.

"""

from . import doxy

class CMacro(ObjectDescription):
    """Document a C macro/define.

    Options
    -------

    hidedef: hide macro definition.
    showloc: show the location of the definition
    """

    option_spec = {
        'hidedef': directives.flag,
    }
    option_spec.update(ObjectDescription.option_spec)

    @property
    def _db(self):
        """Shortcut to get access to the doxygen db."""
        return self.env.doxy_db

    def handle_signature(self, sig, signode):
        """

        Parameters
        ----------

        sig: Signature. It is parsed as a doxy.Target string.
        signode: Where nodes will be appended.

        Return
        ------

        refid for the current object.
        """

        tgt = doxy.Target(sig)

    def add_target_and_index(self, name, sig, signode):
        # type: (Any, unicode, addnodes.desc_signature) -> None
        """
        Add cross-reference IDs and entries to self.indexnode, if applicable.

        Parameters
        ----------

        name: refid for the object.
        sig: Signature. It is parsed as a doxy.Target string.
        """
        return  # do nothing by default



class CObject(ObjectDescription):
    """
    Description of a C language object.
    """

    doc_field_types = [
        TypedField('parameter', label=_('Parameters'),
                   names=('param', 'parameter', 'arg', 'argument'),
                   typerolename='type', typenames=('type',)),
        Field('returnvalue', label=_('Returns'), has_arg=False,
              names=('returns', 'return')),
        Field('returntype', label=_('Return type'), has_arg=False,
              names=('rtype',)),
    ]

    # These C types aren't described anywhere, so don't try to create
    # a cross-reference to them
    stopwords = set((
        'const', 'void', 'char', 'wchar_t', 'int', 'short',
        'long', 'float', 'double', 'unsigned', 'signed', 'FILE',
        'clock_t', 'time_t', 'ptrdiff_t', 'size_t', 'ssize_t',
        'struct', '_Bool',
    ))

    def _parse_type(self, node, ctype):
        # type: (nodes.Node, unicode) -> None
        # add cross-ref nodes for all words
        for part in [_f for _f in wsplit_re.split(ctype) if _f]:  # type: ignore
            tnode = nodes.Text(part, part)
            if part[0] in string.ascii_letters + '_' and \
               part not in self.stopwords:
                pnode = addnodes.pending_xref(
                    '', refdomain='c', reftype='type', reftarget=part,
                    modname=None, classname=None)
                pnode += tnode
                node += pnode
            else:
                node += tnode

    def _parse_arglist(self, arglist):
        # type: (unicode) -> Iterator[unicode]
        while True:
            m = c_funcptr_arg_sig_re.match(arglist)  # type: ignore
            if m:
                yield m.group()
                arglist = c_funcptr_arg_sig_re.sub('', arglist)  # type: ignore
                if ',' in arglist:
                    _, arglist = arglist.split(',', 1)
                else:
                    break
            else:
                if ',' in arglist:
                    arg, arglist = arglist.split(',', 1)
                    yield arg
                else:
                    yield arglist
                    break

    def handle_signature(self, sig, signode):
        # type: (unicode, addnodes.desc_signature) -> unicode
        """Transform a C signature into RST nodes."""
        # first try the function pointer signature regex, it's more specific
        m = c_funcptr_sig_re.match(sig)  # type: ignore
        if m is None:
            m = c_sig_re.match(sig)  # type: ignore
        if m is None:
            raise ValueError('no match')
        rettype, name, arglist, const = m.groups()

        signode += addnodes.desc_type('', '')
        self._parse_type(signode[-1], rettype)
        try:
            classname, funcname = name.split('::', 1)
            classname += '::'
            signode += addnodes.desc_addname(classname, classname)
            signode += addnodes.desc_name(funcname, funcname)
            # name (the full name) is still both parts
        except ValueError:
            signode += addnodes.desc_name(name, name)
        # clean up parentheses from canonical name
        m = c_funcptr_name_re.match(name)
        if m:
            name = m.group(1)

        typename = self.env.ref_context.get('c:type')
        if self.name == 'c:member' and typename:
            fullname = typename + '.' + name
        else:
            fullname = name

        if not arglist:
            if self.objtype == 'function' or \
                    self.objtype == 'macro' and sig.rstrip().endswith('()'):
                # for functions, add an empty parameter list
                signode += addnodes.desc_parameterlist()
            if const:
                signode += addnodes.desc_addname(const, const)
            return fullname

        paramlist = addnodes.desc_parameterlist()
        arglist = arglist.replace('`', '').replace('\\ ', '')  # remove markup
        # this messes up function pointer types, but not too badly ;)
        for arg in self._parse_arglist(arglist):
            arg = arg.strip()
            param = addnodes.desc_parameter('', '', noemph=True)
            try:
                m = c_funcptr_arg_sig_re.match(arg)  # type: ignore
                if m:
                    self._parse_type(param, m.group(1) + '(')
                    param += nodes.emphasis(m.group(2), m.group(2))
                    self._parse_type(param, ')(' + m.group(3) + ')')
                    if m.group(4):
                        param += addnodes.desc_addname(m.group(4), m.group(4))
                else:
                    ctype, argname = arg.rsplit(' ', 1)
                    self._parse_type(param, ctype)
                    # separate by non-breaking space in the output
                    param += nodes.emphasis(' ' + argname, u'\xa0' + argname)
            except ValueError:
                # no argument name given, only the type
                self._parse_type(param, arg)
            paramlist += param
        signode += paramlist
        if const:
            signode += addnodes.desc_addname(const, const)
        return fullname

    def get_index_text(self, name):
        # type: (unicode) -> unicode
        if self.objtype == 'function':
            return _('%s (C function)') % name
        elif self.objtype == 'member':
            return _('%s (C member)') % name
        elif self.objtype == 'macro':
            return _('%s (C macro)') % name
        elif self.objtype == 'type':
            return _('%s (C type)') % name
        elif self.objtype == 'var':
            return _('%s (C variable)') % name
        else:
            return ''

    def add_target_and_index(self, name, sig, signode):
        # type: (unicode, unicode, addnodes.desc_signature) -> None
        # for C API items we add a prefix since names are usually not qualified
        # by a module name and so easily clash with e.g. section titles
        targetname = 'c.' + name
        if targetname not in self.state.document.ids:
            signode['names'].append(targetname)
            signode['ids'].append(targetname)
            signode['first'] = (not self.names)
            self.state.document.note_explicit_target(signode)
            inv = self.env.domaindata['c']['objects']
            if name in inv:
                self.state_machine.reporter.warning(
                    'duplicate C object description of %s, ' % name +
                    'other instance in ' + self.env.doc2path(inv[name][0]),
                    line=self.lineno)
            inv[name] = (self.env.docname, self.objtype)

        indextext = self.get_index_text(name)
        if indextext:
            self.indexnode['entries'].append(('single', indextext,
                                              targetname, '', None))

    def before_content(self):
        # type: () -> None
        self.typename_set = False
        if self.name == 'c:type':
            if self.names:
                self.env.ref_context['c:type'] = self.names[0]
                self.typename_set = True

    def after_content(self):
        # type: () -> None
        if self.typename_set:
            self.env.ref_context.pop('c:type', None)
