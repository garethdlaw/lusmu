"""Tools for visualizing a lusmu graph

Copyright 2013 Eniram Ltd. See the LICENSE file at the top-level directory of
this distribution and at https://github.com/akaihola/lusmu/blob/master/LICENSE

"""

# pylint: disable=W0212
#         Allow access to protected members of client classes
# pylint: disable=W0142
#         Allow * and ** magic

from __future__ import print_function, unicode_literals
import re
from textwrap import dedent

from lusmu.core import SrcNode, OpNode
import subprocess


def collect_nodes(collected_nodes, *args):
    """Collect all nodes belonging to the same graph

    Walks connected nodes recursively.

    Collects nodes recursively in two directions:
    * dependent nodes
    * nodes connected to input ports

    """
    for node in args:
        if node not in collected_nodes:
            collected_nodes.add(node)
            collect_nodes(collected_nodes, *node._dependents)
            if isinstance(node, OpNode):
                collect_nodes(collected_nodes, *node._iterate_inputs())


def get_operation_name(operation):
    """Try to return a good representation of the name of an operation callable"""
    if hasattr(operation, 'name'):
        return operation.name
    if hasattr(operation, '__name__'):
        return operation.__name__
    if hasattr(operation, 'func_name'):
        return operation.func_name
    return operation.__class__.__name__


def format_node_default(node_id, node):
    shape = 'oval' if isinstance(node, SrcNode) else 'box'
    operation = ('{br}{br}<FONT COLOR="#888888">{operation}</FONT>'
                 .format(br=' <BR ALIGN="LEFT"/>',
                         operation=get_operation_name(node._operation))
                 if isinstance(node, OpNode)
                 else '')
    yield ('  {node_id} '
           '[label=<<B>{name}</B>'
           '{operation}>'
           ' shape={shape}];'
           .format(node_id=node_id,
                   name=node.name.replace(':', ':<BR ALIGN="LEFT"/>'),
                   operation=operation,
                   shape=shape))
    yield '  edge [color=blue];'


def graphviz_lines(nodes, node_filter, format_node):
    """Generate source lines for a Graphviz graph definition"""
    all_nodes = set()
    collect_nodes(all_nodes, *nodes)
    if node_filter:
        all_nodes = [n for n in all_nodes if node_filter(n)]
    all_nodes = sorted(all_nodes, key=id)
    source_nodes = [n for n in all_nodes if isinstance(n, SrcNode)]

    yield 'digraph gr {'
    yield '  graph [ dpi = 48 ];'
    yield '  rankdir = LR;'
    yield '  { rank = source;'
    for node in source_nodes:
        yield '    n{};'.format(id(node))
    yield '  }'
    for node in all_nodes:
        for line in format_node('n{}'.format(id(node)), node):
            yield line
        for other in node._dependents:
            if other in all_nodes:
                yield ('  n{node} -> n{other};'
                       .format(node=id(node), other=id(other)))
    yield '}'


def visualize_graph(nodes, filename,
                    node_filter=lambda node: True,
                    format_node=format_node_default):
    """Saves a visualization of given nodes in an image file"""
    image_format = filename.split('.')[-1].lower()
    graphviz = subprocess.Popen(['dot',
                                 '-T{}'.format(image_format),
                                 '-o', filename],
                                stdin=subprocess.PIPE)
    source = '\n'.join(graphviz_lines(nodes,
                                      node_filter,
                                      format_node))
    graphviz.communicate(source.encode('utf-8'))

    # Add some CSS to SVG images
    if image_format == 'svg':
        with open(filename) as svg_file:
            svg = svg_file.read()
        svg = re.sub(r'(<svg\s[^>]*>)',
                     dedent(r'''
                     \1
                     <style type="text/css"><![CDATA[
                         g.node:hover {
                             stroke-width: 2;
                         }
                     ]]></style>
                     '''),
                     svg,
                     re.S)
        with open(filename, 'w') as svg_file:
            svg_file.write(svg)

    return source
