#!/usr/bin/env python3
"""
Proneta XML to Obsidian Markdown Converter

This script parses Proneta XML topology files and generates 
Markdown files for each network device for use in Obsidian.
"""

import xml.etree.ElementTree as ET
import os
from pathlib import Path


def get_text(element, tag_name, default=""):
    """
    Safely extract text from an XML element.
    
    Args:
        element: XML element to search in
        tag_name: Name of the tag to find
        default: Default value if tag not found or empty
        
    Returns:
        Text content of the tag or default value
    """
    child = element.find(tag_name)
    if child is not None and child.text:
        return child.text.strip()
    return default


def sanitize_filename(filename):
    """
    Sanitize filename by removing invalid characters.
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename safe for filesystem
    """
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    return filename


def parse_port(port_element):
    """
    Parse a Port element and extract relevant information.
    
    Args:
        port_element: XML Port element
        
    Returns:
        Dictionary with port information
    """
    port_data = {
        'PortGlobalIndex': get_text(port_element, 'PortGlobalIndex'),
        'PortIfIndex': get_text(port_element, 'PortIfIndex'),
        'PortDesc': get_text(port_element, 'PortDesc'),
        'PortID': get_text(port_element, 'PortID'),
        'MAC': get_text(port_element, 'MAC'),
        'RemotePortID': get_text(port_element, 'RemotePortID'),
        'RemoteNameOfStation': get_text(port_element, 'RemoteNameOfStation'),
        'RemoteMAC': get_text(port_element, 'RemoteMAC'),
    }
    return port_data


def generate_markdown(device_element):
    """
    Generate Markdown content for a device.
    
    Args:
        device_element: XML Device element
        
    Returns:
        Markdown formatted string
    """
    # Extract basic device information
    name_of_station = get_text(device_element, 'NameOfStation', 'unknown')
    ip_address = get_text(device_element, 'IpAddress')
    network_mask = get_text(device_element, 'NetworkMask')
    device_type = get_text(device_element, 'DeviceType')
    mac = get_text(device_element, 'MAC')
    manufacturer_name = get_text(device_element, 'ManufacturerName')
    
    # Start building markdown content
    md_content = []
    md_content.append(f"# {name_of_station}\n")
    md_content.append("## Device Information\n")
    md_content.append(f"- **Name of Station**: {name_of_station}\n")
    md_content.append(f"- **IP Address**: {ip_address}\n")
    md_content.append(f"- **Network Mask**: {network_mask}\n")
    md_content.append(f"- **Device Type**: {device_type}\n")
    md_content.append(f"- **MAC Address**: {mac}\n")
    md_content.append(f"- **Manufacturer**: {manufacturer_name}\n")
    
    # Extract port information from Interfaces/PnInterface/PortList
    interfaces = device_element.find('Interfaces')
    if interfaces is not None:
        pn_interface = interfaces.find('PnInterface')
        if pn_interface is not None:
            port_list = pn_interface.find('PortList')
            if port_list is not None:
                ports = port_list.findall('Port')
                
                if ports:
                    md_content.append("\n## Ports\n")
                    
                    for port in ports:
                        port_data = parse_port(port)
                        
                        # Only include ports with meaningful data
                        port_global_index = port_data['PortGlobalIndex']
                        port_id = port_data['PortID']
                        
                        md_content.append(f"\n### Port {port_global_index} ({port_id})\n")
                        
                        if port_data['PortDesc']:
                            md_content.append(f"- **Description**: {port_data['PortDesc']}\n")
                        
                        md_content.append(f"- **Port ID**: {port_data['PortID']}\n")
                        md_content.append(f"- **MAC**: {port_data['MAC']}\n")
                        
                        # Add remote connection information if available
                        if port_data['RemoteNameOfStation']:
                            md_content.append(f"- **Remote Port ID**: {port_data['RemotePortID']}\n")
                            # Format as Obsidian link
                            remote_station = port_data['RemoteNameOfStation']
                            md_content.append(f"- **Remote Station**: [[{remote_station}]]\n")
                            
                            if port_data['RemoteMAC']:
                                md_content.append(f"- **Remote MAC**: {port_data['RemoteMAC']}\n")
                        else:
                            md_content.append("- **Status**: No remote connection\n")
    
    return ''.join(md_content)


def parse_xml_and_generate_markdown(xml_file_path, output_dir='./net'):
    """
    Parse Proneta XML file and generate Markdown files for each device.
    
    Args:
        xml_file_path: Path to the XML file
        output_dir: Directory where markdown files will be created
    """
    # Create output directory if it doesn't exist
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Parse XML file
    try:
        tree = ET.parse(xml_file_path)
        root = tree.getroot()
    except ET.ParseError as e:
        print(f"Error parsing XML file: {e}")
        return
    except FileNotFoundError:
        print(f"Error: File '{xml_file_path}' not found")
        return
    
    # Find all Device elements in DeviceCollection
    device_collection = root.find('DeviceCollection')
    if device_collection is None:
        print("No DeviceCollection found in XML")
        return
    
    devices = device_collection.findall('Device')
    
    if not devices:
        print("No devices found in XML")
        return
    
    print(f"Found {len(devices)} devices")
    
    # Process each device
    for device in devices:
        name_of_station = get_text(device, 'NameOfStation', 'unknown_device')
        
        # Generate markdown content
        markdown_content = generate_markdown(device)
        
        # Create filename from NameOfStation
        filename = sanitize_filename(name_of_station) + '.md'
        output_file = output_path / filename
        
        # Write markdown file
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
            print(f"Created: {output_file}")
        except Exception as e:
            print(f"Error writing file {output_file}: {e}")


def main():
    """Main entry point of the script."""
    # Default XML file path - can be changed to './sources/proneta.xml' for full version
    xml_file = './resources/proneta.xml'
    
    # Check if full version exists
    full_xml_file = './sources/proneta.xml'
    if os.path.exists(full_xml_file):
        xml_file = full_xml_file
        print(f"Using full version: {xml_file}")
    elif os.path.exists(xml_file):
        print(f"Using test version: {xml_file}")
    else:
        print(f"Error: Neither '{full_xml_file}' nor '{xml_file}' found")
        return
    
    # Parse XML and generate markdown files
    parse_xml_and_generate_markdown(xml_file)
    print("\nConversion complete!")


if __name__ == '__main__':
    main()
