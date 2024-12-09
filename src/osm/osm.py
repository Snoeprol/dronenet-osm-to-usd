from typing import List
import xml.etree.ElementTree as ET
from .bounds import Bounds
from .node import Node
from .way import Way
from .relation import Relation
from .tag import Tag
from .member import Member

class OSM:
    """Main class for handling OpenStreetMap data."""
    def __init__(self, version: str = "0.6", generator: str = None):
        self.version = version
        self.generator = generator
        self.bounds: Bounds = None
        self.nodes: List[Node] = []
        self.ways: List[Way] = []
        self.relations: List[Relation] = []
    
    @classmethod
    def from_xml(cls, xml_path: str) -> 'OSM':
        """Create an OSM object from an XML file."""
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
            
            if root.tag != 'osm':
                raise ValueError("Not a valid OSM file: root element must be 'osm'")
            
            osm = cls(version=root.attrib.get('version'),
                     generator=root.attrib.get('generator'))
            
            # Parse bounds
            bounds_elem = root.find('bounds')
            if bounds_elem is not None:
                osm.bounds = Bounds(
                    float(bounds_elem.attrib['minlat']),
                    float(bounds_elem.attrib['minlon']),
                    float(bounds_elem.attrib['maxlat']),
                    float(bounds_elem.attrib['maxlon']),
                    bounds_elem.attrib.get('origin')
                )
            
            # Parse nodes
            for node_elem in root.findall('node'):
                node = Node(
                    id=int(node_elem.attrib['id']),
                    lat=float(node_elem.attrib['lat']),
                    lon=float(node_elem.attrib['lon']),
                    visible=node_elem.attrib.get('visible', 'true').lower() == 'true',
                    version=int(node_elem.attrib.get('version', 0)),
                    timestamp=node_elem.attrib.get('timestamp'),
                    changeset=int(node_elem.attrib.get('changeset', 0)),
                    uid=int(node_elem.attrib.get('uid', 0)),
                    user=node_elem.attrib.get('user')
                )
                
                # Parse node tags
                for tag_elem in node_elem.findall('tag'):
                    node.tags.append(Tag(tag_elem.attrib['k'], tag_elem.attrib['v']))
                
                osm.nodes.append(node)
            
            # Parse ways
            for way_elem in root.findall('way'):
                way = Way(
                    id=int(way_elem.attrib['id']),
                    visible=way_elem.attrib.get('visible', 'true').lower() == 'true',
                    version=int(way_elem.attrib.get('version', 0)),
                    timestamp=way_elem.attrib.get('timestamp'),
                    changeset=int(way_elem.attrib.get('changeset', 0)),
                    uid=int(way_elem.attrib.get('uid', 0)),
                    user=way_elem.attrib.get('user')
                )
                
                # Parse way nodes
                for nd_elem in way_elem.findall('nd'):
                    way.nodes.append(int(nd_elem.attrib['ref']))
                
                # Parse way tags
                for tag_elem in way_elem.findall('tag'):
                    way.tags.append(Tag(tag_elem.attrib['k'], tag_elem.attrib['v']))
                
                osm.ways.append(way)
            
            # Parse relations
            for rel_elem in root.findall('relation'):
                relation = Relation(
                    id=int(rel_elem.attrib['id']),
                    visible=rel_elem.attrib.get('visible', 'true').lower() == 'true',
                    version=int(rel_elem.attrib.get('version', 0)),
                    timestamp=rel_elem.attrib.get('timestamp'),
                    changeset=int(rel_elem.attrib.get('changeset', 0)),
                    uid=int(rel_elem.attrib.get('uid', 0)),
                    user=rel_elem.attrib.get('user')
                )
                
                # Parse relation members
                for member_elem in rel_elem.findall('member'):
                    relation.members.append(Member(
                        type=member_elem.attrib['type'],
                        ref=int(member_elem.attrib['ref']),
                        role=member_elem.attrib['role']
                    ))
                
                # Parse relation tags
                for tag_elem in rel_elem.findall('tag'):
                    relation.tags.append(Tag(tag_elem.attrib['k'], tag_elem.attrib['v']))
                
                osm.relations.append(relation)
            
            return osm
        except ET.ParseError as e:
            raise ValueError(f"Invalid XML file: {str(e)}")
        except Exception as e:
            raise ValueError(f"Error parsing OSM file: {str(e)}")