"""
RSS Feed Generator for Lacak Emas API

Generates RSS/Atom feeds for gold price updates.
Compatible with n8n RSS node and other feed readers.
"""
from datetime import datetime, date, timedelta
from typing import Optional
import xml.etree.ElementTree as ET
from xml.dom import minidom


def format_price(price: Optional[int]) -> str:
    """Format price to Indonesian Rupiah format"""
    if price is None:
        return "-"
    return f"Rp {price:,}".replace(",", ".")


def generate_rss_feed(
    prices: list[dict],
    title: str = "Lacak Emas - Harga Emas Terkini",
    description: str = "Update harga emas harian dari Galeri24",
    link: str = "https://galeri24.co.id/harga-emas",
    feed_url: str = "",
) -> str:
    """
    Generate RSS 2.0 feed from price data.
    
    Args:
        prices: List of price dicts with vendor, weight, selling_price, etc.
        title: Feed title
        description: Feed description
        link: Website link
        feed_url: Self-referencing feed URL
        
    Returns:
        RSS XML string
    """
    # Create root element
    rss = ET.Element("rss", version="2.0")
    rss.set("xmlns:atom", "http://www.w3.org/2005/Atom")
    
    channel = ET.SubElement(rss, "channel")
    
    # Channel metadata
    ET.SubElement(channel, "title").text = title
    ET.SubElement(channel, "description").text = description
    ET.SubElement(channel, "link").text = link
    ET.SubElement(channel, "language").text = "id"
    ET.SubElement(channel, "lastBuildDate").text = datetime.now().strftime("%a, %d %b %Y %H:%M:%S +0700")
    ET.SubElement(channel, "generator").text = "Lacak Emas API v2.0"
    
    # Self-referencing link (for Atom compatibility)
    if feed_url:
        atom_link = ET.SubElement(channel, "{http://www.w3.org/2005/Atom}link")
        atom_link.set("href", feed_url)
        atom_link.set("rel", "self")
        atom_link.set("type", "application/rss+xml")
    
    # Add items
    for price in prices:
        item = ET.SubElement(channel, "item")
        
        vendor = price.get("vendor", "Unknown")
        weight = price.get("weight", 0)
        selling_price = price.get("selling_price")
        buyback_price = price.get("buyback_price")
        price_date = price.get("date") or price.get("price_date") or date.today().isoformat()
        
        # Title
        ET.SubElement(item, "title").text = f"{vendor} {weight}g - {format_price(selling_price)}"
        
        # Description with details
        desc_parts = [
            f"<b>Vendor:</b> {vendor}",
            f"<b>Berat:</b> {weight} gram",
            f"<b>Harga Jual:</b> {format_price(selling_price)}",
            f"<b>Harga Buyback:</b> {format_price(buyback_price)}",
            f"<b>Tanggal:</b> {price_date}",
        ]
        ET.SubElement(item, "description").text = "<br>".join(desc_parts)
        
        # Link (unique per item)
        ET.SubElement(item, "link").text = f"{link}#{vendor.lower().replace(' ', '-')}-{weight}"
        
        # GUID (unique identifier)
        guid = ET.SubElement(item, "guid")
        guid.text = f"lacak-emas-{vendor}-{weight}-{price_date}"
        guid.set("isPermaLink", "false")
        
        # Publication date
        try:
            pub_date = datetime.strptime(price_date, "%Y-%m-%d")
            ET.SubElement(item, "pubDate").text = pub_date.strftime("%a, %d %b %Y 09:00:00 +0700")
        except:
            ET.SubElement(item, "pubDate").text = datetime.now().strftime("%a, %d %b %Y %H:%M:%S +0700")
        
        # Category
        ET.SubElement(item, "category").text = vendor
    
    # Convert to string with pretty printing
    xml_str = ET.tostring(rss, encoding="unicode")
    dom = minidom.parseString(xml_str)
    return dom.toprettyxml(indent="  ", encoding=None)


def generate_changes_rss_feed(
    changes: list[dict],
    title: str = "Lacak Emas - Perubahan Harga",
    description: str = "Notifikasi perubahan harga emas harian",
    link: str = "https://galeri24.co.id/harga-emas",
    feed_url: str = "",
) -> str:
    """
    Generate RSS feed for price changes (up/down/stable).
    
    This is ideal for n8n triggers - only new items when prices change.
    """
    rss = ET.Element("rss", version="2.0")
    rss.set("xmlns:atom", "http://www.w3.org/2005/Atom")
    
    channel = ET.SubElement(rss, "channel")
    
    # Channel metadata
    ET.SubElement(channel, "title").text = title
    ET.SubElement(channel, "description").text = description
    ET.SubElement(channel, "link").text = link
    ET.SubElement(channel, "language").text = "id"
    ET.SubElement(channel, "lastBuildDate").text = datetime.now().strftime("%a, %d %b %Y %H:%M:%S +0700")
    ET.SubElement(channel, "generator").text = "Lacak Emas API v2.0"
    
    if feed_url:
        atom_link = ET.SubElement(channel, "{http://www.w3.org/2005/Atom}link")
        atom_link.set("href", feed_url)
        atom_link.set("rel", "self")
        atom_link.set("type", "application/rss+xml")
    
    # Add items for price changes
    for change in changes:
        item = ET.SubElement(channel, "item")
        
        vendor = change.get("vendor", "Unknown")
        weight = float(change.get("weight", 0))
        previous_price = change.get("previous_price")
        current_price = change.get("current_price")
        change_amount = change.get("change_amount", 0)
        change_percent = change.get("change_percent", 0)
        trend = change.get("trend", "stable")
        price_date = change.get("price_date") or date.today().isoformat()
        
        # Trend emoji and text
        if trend == "up":
            trend_icon = "📈"
            trend_text = "NAIK"
        elif trend == "down":
            trend_icon = "📉"
            trend_text = "TURUN"
        else:
            trend_icon = "➡️"
            trend_text = "STABIL"
        
        # Title with trend
        title_text = f"{trend_icon} {vendor} {weight}g {trend_text}"
        if change_amount:
            sign = "+" if change_amount > 0 else ""
            title_text += f" {sign}{format_price(change_amount)}"
        
        ET.SubElement(item, "title").text = title_text
        
        # Detailed description
        desc_parts = [
            f"<b>Vendor:</b> {vendor}",
            f"<b>Berat:</b> {weight} gram",
            f"<b>Harga Sebelumnya:</b> {format_price(previous_price)}",
            f"<b>Harga Sekarang:</b> {format_price(current_price)}",
            f"<b>Perubahan:</b> {'+' if change_amount and change_amount > 0 else ''}{format_price(change_amount)} ({change_percent:+.2f}%)",
            f"<b>Trend:</b> {trend_text}",
            f"<b>Tanggal:</b> {price_date}",
        ]
        ET.SubElement(item, "description").text = "<br>".join(desc_parts)
        
        ET.SubElement(item, "link").text = f"{link}#{vendor.lower().replace(' ', '-')}-{weight}"
        
        guid = ET.SubElement(item, "guid")
        guid.text = f"lacak-emas-change-{vendor}-{weight}-{price_date}"
        guid.set("isPermaLink", "false")
        
        try:
            pub_date = datetime.strptime(price_date, "%Y-%m-%d")
            ET.SubElement(item, "pubDate").text = pub_date.strftime("%a, %d %b %Y 09:00:00 +0700")
        except:
            ET.SubElement(item, "pubDate").text = datetime.now().strftime("%a, %d %b %Y %H:%M:%S +0700")
        
        ET.SubElement(item, "category").text = trend
        ET.SubElement(item, "category").text = vendor
    
    xml_str = ET.tostring(rss, encoding="unicode")
    dom = minidom.parseString(xml_str)
    return dom.toprettyxml(indent="  ", encoding=None)


def generate_atom_feed(
    prices: list[dict],
    title: str = "Lacak Emas - Harga Emas Terkini",
    subtitle: str = "Update harga emas harian dari Galeri24",
    feed_url: str = "",
    website_url: str = "https://galeri24.co.id/harga-emas",
) -> str:
    """
    Generate Atom 1.0 feed (alternative to RSS).
    Some feed readers prefer Atom format.
    """
    # Atom namespace
    ns = "http://www.w3.org/2005/Atom"
    ET.register_namespace("", ns)
    
    feed = ET.Element(f"{{{ns}}}feed")
    
    # Feed metadata
    ET.SubElement(feed, f"{{{ns}}}title").text = title
    ET.SubElement(feed, f"{{{ns}}}subtitle").text = subtitle
    ET.SubElement(feed, f"{{{ns}}}id").text = feed_url or website_url
    ET.SubElement(feed, f"{{{ns}}}updated").text = datetime.now().strftime("%Y-%m-%dT%H:%M:%S+07:00")
    
    # Links
    link_self = ET.SubElement(feed, f"{{{ns}}}link")
    link_self.set("href", feed_url)
    link_self.set("rel", "self")
    
    link_alt = ET.SubElement(feed, f"{{{ns}}}link")
    link_alt.set("href", website_url)
    link_alt.set("rel", "alternate")
    
    # Author
    author = ET.SubElement(feed, f"{{{ns}}}author")
    ET.SubElement(author, f"{{{ns}}}name").text = "Lacak Emas API"
    
    # Generator
    generator = ET.SubElement(feed, f"{{{ns}}}generator")
    generator.text = "Lacak Emas API"
    generator.set("version", "2.0")
    
    # Entries
    for price in prices:
        entry = ET.SubElement(feed, f"{{{ns}}}entry")
        
        vendor = price.get("vendor", "Unknown")
        weight = price.get("weight", 0)
        selling_price = price.get("selling_price")
        buyback_price = price.get("buyback_price")
        price_date = price.get("date") or price.get("price_date") or date.today().isoformat()
        
        ET.SubElement(entry, f"{{{ns}}}title").text = f"{vendor} {weight}g - {format_price(selling_price)}"
        ET.SubElement(entry, f"{{{ns}}}id").text = f"lacak-emas-{vendor}-{weight}-{price_date}"
        
        try:
            updated = datetime.strptime(price_date, "%Y-%m-%d").strftime("%Y-%m-%dT09:00:00+07:00")
        except:
            updated = datetime.now().strftime("%Y-%m-%dT%H:%M:%S+07:00")
        ET.SubElement(entry, f"{{{ns}}}updated").text = updated
        
        link = ET.SubElement(entry, f"{{{ns}}}link")
        link.set("href", f"{website_url}#{vendor.lower().replace(' ', '-')}-{weight}")
        
        content = ET.SubElement(entry, f"{{{ns}}}content")
        content.set("type", "html")
        content.text = f"""
        <p><b>Vendor:</b> {vendor}</p>
        <p><b>Berat:</b> {weight} gram</p>
        <p><b>Harga Jual:</b> {format_price(selling_price)}</p>
        <p><b>Harga Buyback:</b> {format_price(buyback_price)}</p>
        """
        
        category = ET.SubElement(entry, f"{{{ns}}}category")
        category.set("term", vendor)
    
    xml_str = ET.tostring(feed, encoding="unicode")
    dom = minidom.parseString(xml_str)
    return dom.toprettyxml(indent="  ", encoding=None)
