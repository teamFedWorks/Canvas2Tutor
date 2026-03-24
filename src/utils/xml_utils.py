"""
XML parsing utilities with namespace support.

This module provides robust XML parsing functions with proper namespace handling
and error reporting.
"""

from lxml import etree
from typing import Optional, List, Dict, Any
from pathlib import Path


def parse_xml_file(file_path: Path, namespaces: Optional[Dict[str, str]] = None) -> Optional[etree._Element]:
    """
    Parse an XML file with proper error handling.
    
    Args:
        file_path: Path to XML file
        namespaces: Optional namespace dictionary
        
    Returns:
        Parsed XML root element or None if parsing fails
        
    Raises:
        FileNotFoundError: If file doesn't exist
        etree.XMLSyntaxError: If XML is malformed
    """
    if not file_path.exists():
        raise FileNotFoundError(f"XML file not found: {file_path}")
    
    try:
        parser = etree.XMLParser(remove_blank_text=True, recover=False)
        tree = etree.parse(str(file_path), parser)
        return tree.getroot()
    except etree.XMLSyntaxError as e:
        raise etree.XMLSyntaxError(
            f"Failed to parse XML file {file_path}: {str(e)}"
        )


def parse_xml_string(xml_string: str) -> Optional[etree._Element]:
    """
    Parse an XML string.
    
    Args:
        xml_string: XML content as string
        
    Returns:
        Parsed XML root element or None if parsing fails
    """
    try:
        parser = etree.XMLParser(remove_blank_text=True, recover=False)
        return etree.fromstring(xml_string.encode('utf-8'), parser)
    except etree.XMLSyntaxError as e:
        raise etree.XMLSyntaxError(f"Failed to parse XML string: {str(e)}")


def find_element(
    root: etree._Element,
    xpath: str,
    namespaces: Optional[Dict[str, str]] = None
) -> Optional[etree._Element]:
    """
    Find a single element using XPath.
    
    Args:
        root: Root element to search from
        xpath: XPath expression
        namespaces: Namespace dictionary
        
    Returns:
        First matching element or None
    """
    try:
        result = root.xpath(xpath, namespaces=namespaces or {})
        if result and isinstance(result, list):
            return result[0] if len(result) > 0 else None
        return result if isinstance(result, etree._Element) else None
    except etree.XPathEvalError:
        return None


def find_elements(
    root: etree._Element,
    xpath: str,
    namespaces: Optional[Dict[str, str]] = None
) -> List[etree._Element]:
    """
    Find all elements matching XPath.
    
    Args:
        root: Root element to search from
        xpath: XPath expression
        namespaces: Namespace dictionary
        
    Returns:
        List of matching elements (empty list if none found)
    """
    try:
        result = root.xpath(xpath, namespaces=namespaces or {})
        if isinstance(result, list):
            return [elem for elem in result if isinstance(elem, etree._Element)]
        return []
    except etree.XPathEvalError:
        return []


def get_element_text(
    element: Optional[etree._Element],
    default: str = ""
) -> str:
    """
    Safely get text content from an element.
    
    Args:
        element: Element to extract text from
        default: Default value if element is None or has no text
        
    Returns:
        Element text or default value
    """
    if element is None:
        return default
    
    text = element.text
    return text.strip() if text else default


def get_element_attribute(
    element: Optional[etree._Element],
    attribute: str,
    default: str = ""
) -> str:
    """
    Safely get an attribute value from an element.
    
    Args:
        element: Element to extract attribute from
        attribute: Attribute name
        default: Default value if element is None or attribute doesn't exist
        
    Returns:
        Attribute value or default
    """
    if element is None:
        return default
    
    return element.get(attribute, default)


def element_to_string(element: etree._Element, pretty: bool = False) -> str:
    """
    Convert an XML element to string.
    
    Args:
        element: Element to convert
        pretty: Whether to pretty-print
        
    Returns:
        XML string
    """
    return etree.tostring(
        element,
        encoding='unicode',
        pretty_print=pretty,
        method='xml'
    )


def get_inner_html(element: etree._Element) -> str:
    """
    Get the inner HTML content of an element (children only, not the element itself).
    
    Args:
        element: Element to extract inner HTML from
        
    Returns:
        Inner HTML as string
    """
    # Get text before first child
    html = element.text or ""
    
    # Add all children
    for child in element:
        html += etree.tostring(child, encoding='unicode', method='html')
    
    return html.strip()


def validate_xml_schema(
    xml_file: Path,
    schema_file: Path
) -> tuple[bool, Optional[str]]:
    """
    Validate an XML file against an XSD schema.
    
    Args:
        xml_file: Path to XML file
        schema_file: Path to XSD schema file
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        schema_doc = etree.parse(str(schema_file))
        schema = etree.XMLSchema(schema_doc)
        
        xml_doc = etree.parse(str(xml_file))
        
        is_valid = schema.validate(xml_doc)
        error_msg = None if is_valid else str(schema.error_log)
        
        return is_valid, error_msg
    except Exception as e:
        return False, str(e)


def remove_namespaces(root: etree._Element) -> etree._Element:
    """
    Remove all namespaces from an XML element tree.
    Useful for simplified XPath queries.
    
    Args:
        root: Root element
        
    Returns:
        Root element with namespaces removed
    """
    for elem in root.iter():
        # Remove namespace from tag
        if '}' in elem.tag:
            elem.tag = elem.tag.split('}', 1)[1]
        
        # Remove namespace declarations
        elem.attrib.pop('{http://www.w3.org/2001/XMLSchema-instance}schemaLocation', None)
    
    return root
