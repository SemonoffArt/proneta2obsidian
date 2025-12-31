#!/usr/bin/env python3
"""
Proneta XML to Obsidian Markdown Converter

This script parses Proneta XML topology files and generates 
Markdown files for each network device for use in Obsidian.
"""

import xml.etree.ElementTree as ET
import os
import re
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


def clean_station_name(name):
    """
    Clean station name by removing 'xd' and 'xb' patterns according to rules:
    - If 'xd' is followed by digits, remove 'xd', then remove last 4 characters
    - Remove all occurrences of 'xb'
    
    Args:
        name: Original station name
        
    Returns:
        Cleaned station name
    """
    if not name:
        return name
    
    # Rule 1: Remove 'xd' when followed by digits
    # This handles cases like 'xd993' -> '993' or 'xd02' -> '02'
    cleaned = re.sub(r'xd(?=\d)', '', name)

    # Rule 2: Remove all occurrences of 'xb'
    cleaned = cleaned.replace('xb', '_')

    cleaned = cleaned.replace('xa', ' ')

    # Rule 3: If first rule was applied (string changed), remove last 4 characters
    # Otherwise, if 'xd' still exists (not followed by digits), remove last 4 characters
    if cleaned != name:
        # First rule was applied, remove last 4 characters
        cleaned = cleaned[:-4]
    

    return cleaned


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
        'MauType': get_text(port_element, 'MauType'),
    }
    return port_data


def generate_markdown(device_element, disable_links=False, scalance_disable_links=None):
    """
    Generate Markdown content for a device.
    
    Args:
        device_element: XML Device element
        disable_links: If True, render RemoteNameOfStation as plain text instead of [[links]]
        scalance_disable_links: Set of RemoteNameOfStation values that should not be rendered as links
                                (used only for SCALANCE devices)
        
    Returns:
        Markdown formatted string
    """
    # Extract basic device information
    name_of_station_raw = get_text(device_element, 'NameOfStation', '')
    
    # If NameOfStation is empty, use DeviceType + IpAddress
    if not name_of_station_raw:
        device_type = get_text(device_element, 'DeviceType', 'unknown')
        ip_address = get_text(device_element, 'IpAddress', 'no-ip')
        name_of_station_raw = f"{device_type}_{ip_address}"
    
    name_of_station = clean_station_name(name_of_station_raw)
    ip_address = get_text(device_element, 'IpAddress')
    network_mask = get_text(device_element, 'NetworkMask')
    device_type = get_text(device_element, 'DeviceType')
    mac = get_text(device_element, 'MAC')
    manufacturer_name = get_text(device_element, 'ManufacturerName')
    location = get_text(device_element, 'Location')
    descriptor = get_text(device_element, 'Descriptor')
    
    # Check if current device is SCALANCE
    is_scalance = 'scalance' in device_type.lower() if device_type else False
    
    # Start building markdown content
    md_content = []
    md_content.append(f"# {name_of_station}\n")
    md_content.append("## Device Information\n")
    md_content.append(f"- **Name of Station**: {name_of_station}\n")
    md_content.append(f"- **Name Original**: {name_of_station_raw}\n")
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
                    # Filter ports to only include those with remote connections
                    connected_ports = [port for port in ports if get_text(port, 'RemoteNameOfStation')]
                    
                    if connected_ports:
                        md_content.append("\n## Ports\n")
                        
                        for port in connected_ports:
                            port_data = parse_port(port)
                            
                            # Only include ports with meaningful data
                            port_if_index = port_data['PortIfIndex']
                            port_id = port_data['PortID']
                            
                            md_content.append(f"\n### Port {port_if_index} ({port_id})\n")
                            
                            if port_data['PortDesc']:
                                md_content.append(f"- **Description**: {port_data['PortDesc']}\n")
                            
                            md_content.append(f"- **Port ID**: {port_data['PortID']}\n")
                            md_content.append(f"- **MAC**: {port_data['MAC']}\n")
                            
                            # Add remote connection information
                            md_content.append(f"- **Remote Port ID**: {port_data['RemotePortID']}\n")
                            # Format as Obsidian link with cleaned name (or plain text if links disabled)
                            remote_station_raw = port_data['RemoteNameOfStation']
                            remote_station = clean_station_name(remote_station_raw)
                            
                            # Determine if this specific remote connection should be a link
                            should_disable_link = disable_links
                            
                            # For SCALANCE devices, check if this remote is in the disable list
                            if is_scalance and scalance_disable_links and remote_station_raw in scalance_disable_links:
                                should_disable_link = True
                            
                            if should_disable_link:
                                # Render as plain text without link
                                md_content.append(f"- **Remote Station**: {remote_station}\n")
                            else:
                                # Render as Obsidian link
                                md_content.append(f"- **Remote Station**: [[{remote_station}]]\n")
                            
                            if port_data['RemoteMAC']:
                                md_content.append(f"- **Remote MAC**: {port_data['RemoteMAC']}\n")
    
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
    
    # Delete all existing .md files in the output directory
    print(f"Cleaning output directory: {output_path}")
    md_files = list(output_path.glob('*.md'))
    if md_files:
        for md_file in md_files:
            try:
                md_file.unlink()
                print(f"Deleted: {md_file}")
            except Exception as e:
                print(f"Warning: Could not delete {md_file}: {e}")
        print(f"Deleted {len(md_files)} existing .md files\n")
    else:
        print("No existing .md files to delete\n")
    
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
    
    # Initialize statistics counters
    stats = {
        'total_devices': len(devices),
        'device_types': {},
        'manufacturers': {},
        'total_ports': 0,
        'connected_ports': 0,
        'devices_with_links': 0,
        'devices_without_links': 0,
        'files_created': 0,
        'files_failed': 0
    }
    
    # Build a map of devices that are referenced by unmanaged switches or SCALANCE
    # These devices should NOT have their RemoteNameOfStation rendered as links
    devices_referenced_by_switches = set()
    devices_referenced_by_unmanaged = set()
    devices_referenced_by_scalance = set()
    
    for device in devices:
        device_type = get_text(device, 'DeviceType', '').lower()
        
        # Check if this device is an unmanaged switch or SCALANCE
        is_unmanaged = 'unmanaged switch' in device_type
        is_scalance = 'scalance' in device_type
        
        if is_unmanaged or is_scalance:
            # Find all ports and their remote connections
            interfaces = device.find('Interfaces')
            if interfaces is not None:
                pn_interface = interfaces.find('PnInterface')
                if pn_interface is not None:
                    port_list = pn_interface.find('PortList')
                    if port_list is not None:
                        ports = port_list.findall('Port')
                        for port in ports:
                            remote_station = get_text(port, 'RemoteNameOfStation')
                            if remote_station:
                                devices_referenced_by_switches.add(remote_station)
                                
                                if is_unmanaged:
                                    devices_referenced_by_unmanaged.add(remote_station)
                                if is_scalance:
                                    devices_referenced_by_scalance.add(remote_station)
    
    # Find devices referenced by BOTH unmanaged switches AND SCALANCE
    # For SCALANCE devices, these remotes should not be rendered as links
    scalance_dual_referenced = devices_referenced_by_unmanaged & devices_referenced_by_scalance
    
    # Process each device
    for device in devices:
        name_of_station_raw = get_text(device, 'NameOfStation', '')
        
        # If NameOfStation is empty, use DeviceType + IpAddress
        if not name_of_station_raw:
            device_type = get_text(device, 'DeviceType', 'unknown')
            ip_address = get_text(device, 'IpAddress', 'no-ip')
            name_of_station_raw = f"{device_type}_{ip_address}"
        
        name_of_station = clean_station_name(name_of_station_raw)
        device_type = get_text(device, 'DeviceType', 'Unknown')
        manufacturer = get_text(device, 'ManufacturerName', 'Unknown')
        device_type_lower = device_type.lower()
        
        # Update device type statistics
        stats['device_types'][device_type] = stats['device_types'].get(device_type, 0) + 1
        
        # Update manufacturer statistics
        stats['manufacturers'][manufacturer] = stats['manufacturers'].get(manufacturer, 0) + 1
        
        # Count ports
        interfaces = device.find('Interfaces')
        device_port_count = 0
        device_connected_count = 0
        
        if interfaces is not None:
            pn_interface = interfaces.find('PnInterface')
            if pn_interface is not None:
                port_list = pn_interface.find('PortList')
                if port_list is not None:
                    ports = port_list.findall('Port')
                    device_port_count = len(ports)
                    connected_ports = [port for port in ports if get_text(port, 'RemoteNameOfStation')]
                    device_connected_count = len(connected_ports)
        
        stats['total_ports'] += device_port_count
        stats['connected_ports'] += device_connected_count
        
        # Check condition A: current device is NOT unmanaged switch or SCALANCE
        is_not_switch = 'unmanaged switch' not in device_type_lower and 'scalance' not in device_type_lower
        
        # Check condition B: current device is referenced by a switch
        is_referenced_by_switch = name_of_station_raw in devices_referenced_by_switches
        
        # Determine if links should be disabled for this device
        disable_links = is_not_switch and is_referenced_by_switch
        
        if disable_links or device_connected_count == 0:
            stats['devices_without_links'] += 1
        else:
            stats['devices_with_links'] += 1
        
        # Generate markdown content with link control
        # Pass scalance_dual_referenced to suppress links for SCALANCE devices
        markdown_content = generate_markdown(device, disable_links, scalance_dual_referenced)
        
        # Create filename from cleaned NameOfStation
        filename = sanitize_filename(name_of_station) + '.md'
        output_file = output_path / filename
        
        # Write markdown file
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
            print(f"Created: {output_file}")
            stats['files_created'] += 1
        except Exception as e:
            print(f"Error writing file {output_file}: {e}")
            stats['files_failed'] += 1
    
    # Print statistics
    print("\n" + "="*60)
    print("📊 NETWORK STATISTICS")
    print("="*60)
    
    print(f"\n🔌 Total Devices: {stats['total_devices']}")
    print(f"✅ Files Created: {stats['files_created']}")
    if stats['files_failed'] > 0:
        print(f"❌ Files Failed: {stats['files_failed']}")
    
    print(f"\n📡 Port Statistics:")
    print(f"  • Total Ports: {stats['total_ports']}")
    print(f"  • Connected Ports: {stats['connected_ports']}")
    if stats['total_ports'] > 0:
        connection_rate = (stats['connected_ports'] / stats['total_ports']) * 100
        print(f"  • Connection Rate: {connection_rate:.1f}%")
    
    print(f"\n🔗 Link Statistics:")
    print(f"  • Devices with Links: {stats['devices_with_links']}")
    print(f"  • Devices without Links: {stats['devices_without_links']}")
    
    print(f"\n🏭 Device Types ({len(stats['device_types'])} types):")
    sorted_types = sorted(stats['device_types'].items(), key=lambda x: x[1], reverse=True)
    for device_type, count in sorted_types[:]:  # Show top 10
        print(f"  • {device_type}: {count}")
    # if len(sorted_types) > 10:
    #     print(f"  ... and {len(sorted_types) - 10} more types")
    
    print(f"\n🏢 Manufacturers ({len(stats['manufacturers'])} total):")
    sorted_manufacturers = sorted(stats['manufacturers'].items(), key=lambda x: x[1], reverse=True)
    for manufacturer, count in sorted_manufacturers[:]:  # Show top 5
        if manufacturer and manufacturer != 'Unknown':
            print(f"  • {manufacturer}: {count}")
    # if len(sorted_manufacturers) > 5:
    #     print(f"  ... and {len(sorted_manufacturers) - 5} more manufacturers")
    
    print("\n" + "="*60)


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
