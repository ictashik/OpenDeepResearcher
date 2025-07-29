import streamlit as st
import pandas as pd
from src.utils.data_manager import load_extracted_data, save_final_report, load_final_report, get_project_dir
from src.utils.ollama_client import OllamaClient
from src.utils.data_manager import load_config
from src.utils.streamlit_utils import safe_dataframe, safe_download_button
from datetime import datetime
import io
import base64
import re
try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    import markdown2
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

def create_pdf_from_markdown(markdown_content, title="Systematic Review Report"):
    """Convert markdown content to PDF using reportlab with improved formatting."""
    if not PDF_AVAILABLE:
        return None
    
    try:
        # Create a buffer to store PDF
        buffer = io.BytesIO()
        
        # Create PDF document with pageBreakQuietly to handle large tables
        doc = SimpleDocTemplate(buffer, pagesize=A4, 
                              rightMargin=inch, leftMargin=inch,
                              topMargin=inch, bottomMargin=inch,
                              allowSplitting=1, showBoundary=0)
        
        # Get styles
        styles = getSampleStyleSheet()
        
        # Define custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=20,
            spaceAfter=24,
            spaceBefore=12,
            alignment=1,  # Center alignment
            textColor=colors.HexColor('#2c3e50')
        )
        
        h1_style = ParagraphStyle(
            'CustomH1',
            parent=styles['Heading1'],
            fontSize=16,
            spaceAfter=12,
            spaceBefore=20,
            textColor=colors.HexColor('#2c3e50')
        )
        
        h2_style = ParagraphStyle(
            'CustomH2',
            parent=styles['Heading2'],
            fontSize=14,
            spaceAfter=10,
            spaceBefore=16,
            textColor=colors.HexColor('#34495e')
        )
        
        h3_style = ParagraphStyle(
            'CustomH3',
            parent=styles['Heading3'],
            fontSize=12,
            spaceAfter=8,
            spaceBefore=12,
            textColor=colors.HexColor('#5d6d7e')
        )
        
        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontSize=11,
            spaceAfter=6,
            leading=16,
            textColor=colors.black
        )
        
        # Build story
        story = []
        
        # Process content line by line with better markdown parsing
        lines = markdown_content.split('\n')
        i = 0
        
        # Track if we're in a table
        in_table = False
        table_data = []
        
        while i < len(lines):
            line = lines[i].rstrip()
            
            # Skip empty lines but add spacing
            if not line:
                # If we were in a table, process it
                if in_table and table_data:
                    table = create_table_from_data(table_data)
                    if table:
                        # Handle both single table objects and lists of elements
                        if isinstance(table, list):
                            story.extend(table)
                        else:
                            story.append(table)
                        story.append(Spacer(1, 12))
                    else:
                        # Try alternative table creation for problematic tables
                        alt_table = create_alternative_table(table_data)
                        if alt_table:
                            if isinstance(alt_table, list):
                                story.extend(alt_table)
                            else:
                                story.append(alt_table)
                            story.append(Spacer(1, 12))
                    table_data = []
                    in_table = False
                else:
                    story.append(Spacer(1, 6))
                i += 1
                continue
            
            # Check if this line is a table row with improved detection
            if is_table_row(line):
                # This might be a table row
                if not in_table:
                    in_table = True
                    table_data = []
                
                # Parse table row
                cells = parse_table_row(line)
                
                if cells:  # Only add non-empty rows
                    table_data.append(cells)
                
                i += 1
                continue
            else:
                # Not a table line, so if we were in a table, process it
                if in_table and table_data:
                    table = create_table_from_data(table_data)
                    if table:
                        # Handle both single table objects and lists of elements
                        if isinstance(table, list):
                            story.extend(table)
                        else:
                            story.append(table)
                        story.append(Spacer(1, 12))
                    else:
                        # Try alternative table creation
                        alt_table = create_alternative_table(table_data)
                        if alt_table:
                            if isinstance(alt_table, list):
                                story.extend(alt_table)
                            else:
                                story.append(alt_table)
                            story.append(Spacer(1, 12))
                    table_data = []
                    in_table = False
            
            # Handle headers
            if line.startswith('# '):
                text = line[2:].strip()
                if not story:  # First element
                    story.append(Paragraph(text, title_style))
                else:
                    story.append(Paragraph(text, h1_style))
            elif line.startswith('## '):
                text = line[3:].strip()
                story.append(Paragraph(text, h2_style))
            elif line.startswith('### '):
                text = line[4:].strip()
                story.append(Paragraph(text, h3_style))
            elif line.startswith('---'):
                story.append(Spacer(1, 12))
                story.append(Paragraph('<para alignment="center">_______________</para>', normal_style))
                story.append(Spacer(1, 12))
            else:
                # Handle regular content with inline formatting
                processed_line = process_inline_markdown(line)
                
                # Handle lists
                if line.startswith('- ') or line.startswith('* '):
                    text = process_inline_markdown(line[2:].strip())
                    story.append(Paragraph(f"• {text}", normal_style))
                elif line.startswith('1. ') or line.startswith('2. ') or line.startswith('3. '):
                    # Handle numbered lists
                    parts = line.split('. ', 1)
                    if len(parts) == 2:
                        number = parts[0]
                        text = process_inline_markdown(parts[1])
                        story.append(Paragraph(f"{number}. {text}", normal_style))
                    else:
                        story.append(Paragraph(processed_line, normal_style))
                else:
                    # Regular paragraph
                    if processed_line.strip():
                        story.append(Paragraph(processed_line, normal_style))
            
            i += 1
        
        # Handle any remaining table at the end
        if in_table and table_data:
            table = create_table_from_data(table_data)
            if table:
                if isinstance(table, list):
                    story.extend(table)
                else:
                    story.append(table)
            else:
                alt_table = create_alternative_table(table_data)
                if alt_table:
                    if isinstance(alt_table, list):
                        story.extend(alt_table)
                    else:
                        story.append(alt_table)
        
        # Build PDF
        doc.build(story)
        
        # Get PDF data
        pdf_data = buffer.getvalue()
        buffer.close()
        
        return pdf_data
        
    except Exception as e:
        st.error(f"Error creating PDF: {str(e)}")
        return None

def is_table_row(line):
    """Enhanced table row detection."""
    line = line.strip()
    if not line:
        return False
    
    # Must contain at least 2 pipe characters
    if line.count('|') < 2:
        return False
    
    # Skip separator rows
    if all(c in '-|: \t' for c in line):
        return False
    
    return True

def parse_table_row(line):
    """Enhanced table row parsing."""
    line = line.strip()
    
    # Handle different formats
    if line.startswith('|') and line.endswith('|'):
        # Standard format: | col1 | col2 | col3 |
        cells = [cell.strip() for cell in line.split('|')[1:-1]]
    else:
        # Alternative format: col1 | col2 | col3
        cells = [cell.strip() for cell in line.split('|')]
    
    # Remove empty cells at start/end and filter out separator patterns
    cells = [cell for cell in cells if cell and not all(c in '-: \t' for c in cell)]
    
    return cells if cells else None

def create_alternative_table(table_data):
    """Alternative table creation for problematic tables."""
    try:
        if not table_data:
            return None
        
        # Create a simple text-based table representation
        from reportlab.platypus import Paragraph
        from reportlab.lib.styles import getSampleStyleSheet
        styles = getSampleStyleSheet()
        
        table_lines = []
        
        # Calculate max width for each column
        max_cols = max(len(row) for row in table_data)
        col_widths = []
        
        for col in range(max_cols):
            max_width = 0
            for row in table_data:
                if col < len(row):
                    max_width = max(max_width, len(str(row[col])))
            col_widths.append(min(max_width + 2, 20))  # Limit column width
        
        # Format each row
        for i, row in enumerate(table_data):
            formatted_cells = []
            for j in range(max_cols):
                cell_content = str(row[j]) if j < len(row) else ""
                # Truncate if too long
                cell_content = cell_content[:col_widths[j]-1] if len(cell_content) > col_widths[j]-1 else cell_content
                formatted_cells.append(cell_content.ljust(col_widths[j]))
            
            row_text = " | ".join(formatted_cells)
            
            if i == 0:
                # Header row
                table_lines.append(f"<b>{row_text}</b>")
                table_lines.append("-" * len(row_text.replace("<b>", "").replace("</b>", "")))
            else:
                table_lines.append(row_text)
        
        # Join lines
        table_content = "<br/>".join(table_lines)
        
        # Create paragraph
        table_para = Paragraph(f'<font name="Courier" size="8">{table_content}</font>', styles['Normal'])
        table_para.spaceBefore = 12
        table_para.spaceAfter = 12
        
        return table_para
        
    except Exception as e:
        return None

def create_table_from_data(table_data):
    """Create a reportlab Table from parsed table data with enhanced handling for wide tables."""
    if not table_data:
        return None
    
    try:
        # For very wide tables (more than 6 columns), use a different approach
        max_cols = max(len(row) for row in table_data) if table_data else 0
        if max_cols == 0:
            return None
        
        # If table is too wide, split into multiple tables or use text format
        if max_cols > 6:
            return create_wide_table_alternative(table_data)
        
        # Calculate available width (page width minus margins)
        available_width = A4[0] - 2 * inch
        
        # Calculate column widths dynamically based on content
        col_widths = calculate_optimal_column_widths(table_data, available_width, max_cols)
        
        # Ensure all rows have the same number of columns
        normalized_data = []
        for row in table_data:
            # Pad rows to have the same number of columns
            while len(row) < max_cols:
                row.append('')
            # Truncate rows that are too long and clean content
            clean_row = []
            for i, cell in enumerate(row[:max_cols]):
                # Clean cell content and truncate if necessary
                cell_content = str(cell).strip()
                if len(cell_content) > 80:  # Truncate very long content
                    cell_content = cell_content[:77] + "..."
                clean_row.append(cell_content)
            normalized_data.append(clean_row)
        
        # Process table data with appropriate cell formatting
        processed_data = []
        for i, row in enumerate(normalized_data):
            processed_row = []
            for j, cell in enumerate(row):
                cell_width = col_widths[j] if j < len(col_widths) else col_widths[-1]
                # Use Paragraph for header row and long content
                if i == 0 or len(str(cell)) > 20:
                    from reportlab.platypus import Paragraph
                    from reportlab.lib.styles import getSampleStyleSheet
                    styles = getSampleStyleSheet()
                    
                    if i == 0:  # Header row
                        cell_style = ParagraphStyle(
                            'HeaderCell',
                            parent=styles['Normal'],
                            fontSize=7,
                            fontName='Helvetica-Bold',
                            leading=8,
                            wordWrap='LTR',
                            alignment=1  # Center alignment for headers
                        )
                    else:  # Data row
                        cell_style = ParagraphStyle(
                            'DataCell',
                            parent=styles['Normal'],
                            fontSize=6,
                            leading=7,
                            wordWrap='LTR'
                        )
                    
                    processed_row.append(Paragraph(str(cell), cell_style))
                else:
                    processed_row.append(str(cell))
            processed_data.append(processed_row)
        
        # Create table with calculated column widths
        table = Table(processed_data, colWidths=col_widths, repeatRows=1)
        
        # Enhanced table styling
        table_style = TableStyle([
            # Header row styling
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4472C4')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 7),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            
            # Data rows styling
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 6),
            ('ALIGN', (0, 1), (-1, -1), 'LEFT'),
            
            # Grid and borders
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('LINEBELOW', (0, 0), (-1, 0), 2, colors.black),
            
            # Padding - reduced for space efficiency
            ('LEFTPADDING', (0, 0), (-1, -1), 2),
            ('RIGHTPADDING', (0, 0), (-1, -1), 2),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            
            # Word wrap
            ('WORDWRAP', (0, 0), (-1, -1), True),
            ('SPLITLONGWORDS', (0, 0), (-1, -1), True),
        ])
        
        # Add alternating row colors for better readability
        for i in range(1, len(processed_data)):
            if i % 2 == 0:
                table_style.add('BACKGROUND', (0, i), (-1, i), colors.HexColor('#F2F2F2'))
        
        table.setStyle(table_style)
        table.hAlign = 'LEFT'
        table.spaceBefore = 12
        table.spaceAfter = 12
        
        return table
        
    except Exception as e:
        # Always fall back to alternative table creation
        return create_wide_table_alternative(table_data)

def calculate_optimal_column_widths(table_data, available_width, max_cols):
    """Calculate optimal column widths based on content."""
    try:
        # Analyze content to determine appropriate widths
        col_content_lengths = []
        for col in range(max_cols):
            max_length = 0
            for row in table_data:
                if col < len(row):
                    content_length = len(str(row[col]))
                    max_length = max(max_length, content_length)
            col_content_lengths.append(max_length)
        
        # Calculate proportional widths
        total_content = sum(col_content_lengths)
        if total_content == 0:
            return [available_width / max_cols] * max_cols
        
        # Minimum and maximum column widths
        min_width = 0.4 * inch
        max_width = 2.0 * inch
        
        col_widths = []
        for length in col_content_lengths:
            # Proportional width based on content
            prop_width = (length / total_content) * available_width
            # Constrain within bounds
            width = max(min_width, min(prop_width, max_width))
            col_widths.append(width)
        
        # Adjust if total exceeds available width
        total_width = sum(col_widths)
        if total_width > available_width:
            scale_factor = available_width / total_width
            col_widths = [w * scale_factor for w in col_widths]
        
        return col_widths
        
    except Exception:
        # Fallback to equal distribution
        return [available_width / max_cols] * max_cols

def create_wide_table_alternative(table_data):
    """Alternative approach for very wide tables - create as formatted study summaries."""
    try:
        from reportlab.platypus import Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet
        styles = getSampleStyleSheet()
        
        if not table_data:
            return None
        
        # Create table as a series of formatted study summaries
        table_elements = []
        
        # Section title style
        title_style = ParagraphStyle(
            'StudySummaryTitle',
            parent=styles['Heading3'],
            fontSize=12,
            spaceAfter=8,
            spaceBefore=16,
            textColor=colors.HexColor('#2c3e50'),
            fontName='Helvetica-Bold'
        )
        
        # Study header style
        study_header_style = ParagraphStyle(
            'StudyHeader',
            parent=styles['Normal'],
            fontSize=10,
            fontName='Helvetica-Bold',
            textColor=colors.HexColor('#4472C4'),
            spaceAfter=4,
            spaceBefore=8
        )
        
        # Study data style
        study_data_style = ParagraphStyle(
            'StudyData',
            parent=styles['Normal'],
            fontSize=9,
            leftIndent=15,
            spaceAfter=3,
            leading=12
        )
        
        # Key findings style
        findings_style = ParagraphStyle(
            'FindingsStyle',
            parent=styles['Normal'],
            fontSize=9,
            leftIndent=15,
            spaceAfter=6,
            leading=12,
            textColor=colors.HexColor('#2c3e50')
        )
        
        if table_data:
            # Add section title
            table_elements.append(Paragraph("Study Characteristics and Findings", title_style))
            
            header_row = table_data[0]
            
            # Process each study as a formatted summary
            for row_idx, row in enumerate(table_data[1:], 1):
                # Create study header
                table_elements.append(Paragraph(f"Study {row_idx}", study_header_style))
                
                # Group related information
                study_info = []
                design_info = []
                results_info = []
                limitations_info = []
                
                for col_idx, (header, cell) in enumerate(zip(header_row, row)):
                    cell_content = str(cell).strip()
                    
                    # Skip empty or "Not found" values
                    if not cell_content or cell_content.lower() in ["not found", "nan", ""]:
                        continue
                    
                    # Clean header name
                    clean_header = header.replace('_', ' ').replace('Article ID', 'ID').title()
                    
                    # Categorize information
                    if any(word in header.lower() for word in ['sample', 'design', 'pages', 'length']):
                        design_info.append(f"{clean_header}: {cell_content}")
                    elif any(word in header.lower() for word in ['intervention', 'outcome', 'effect']):
                        results_info.append(f"{clean_header}: {cell_content}")
                    elif 'limitation' in header.lower():
                        limitations_info.append(cell_content)
                    else:
                        study_info.append(f"{clean_header}: {cell_content}")
                
                # Format study information
                if study_info:
                    study_text = " | ".join(study_info)
                    table_elements.append(Paragraph(f"<b>Study Details:</b> {study_text}", study_data_style))
                
                if design_info:
                    design_text = " | ".join(design_info)
                    table_elements.append(Paragraph(f"<b>Study Design:</b> {design_text}", study_data_style))
                
                if results_info:
                    results_text = " | ".join(results_info)
                    # Truncate very long results
                    if len(results_text) > 200:
                        results_text = results_text[:197] + "..."
                    table_elements.append(Paragraph(f"<b>Key Findings:</b> {results_text}", findings_style))
                
                if limitations_info:
                    for limitation in limitations_info:
                        # Truncate very long limitations
                        if len(limitation) > 150:
                            limitation = limitation[:147] + "..."
                        table_elements.append(Paragraph(f"<b>Limitations:</b> {limitation}", study_data_style))
                
                # Add spacing between studies
                table_elements.append(Spacer(1, 8))
        
        return table_elements
        
    except Exception as e:
        # Ultimate fallback
        return create_simple_table_fallback(table_data)

def create_simple_table_fallback(table_data):
    """Enhanced fallback method to create narrative-style study descriptions."""
    try:
        from reportlab.platypus import Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet
        styles = getSampleStyleSheet()
        
        if not table_data:
            return None
        
        # Create a narrative-style representation
        table_elements = []
        
        # Section title style
        title_style = ParagraphStyle(
            'NarrativeTitle',
            parent=styles['Heading3'],
            fontSize=11,
            fontName='Helvetica-Bold',
            spaceAfter=10,
            textColor=colors.HexColor('#2c3e50')
        )
        
        # Paragraph style for study descriptions
        narrative_style = ParagraphStyle(
            'NarrativeText',
            parent=styles['Normal'],
            fontSize=9,
            spaceAfter=8,
            leading=13,
            firstLineIndent=0.2*inch,
            leftIndent=0.1*inch
        )
        
        if table_data and len(table_data) > 1:
            # Add section title
            table_elements.append(Paragraph("Included Studies Overview", title_style))
            
            header_row = table_data[0]
            
            # Create narrative descriptions for each study
            for row_idx, row in enumerate(table_data[1:], 1):
                study_info = {}
                
                # Extract meaningful information
                for col_idx, (header, cell) in enumerate(zip(header_row, row)):
                    cell_content = str(cell).strip()
                    if cell_content and cell_content.lower() not in ["not found", "nan", ""]:
                        clean_header = header.lower().replace('_', ' ')
                        study_info[clean_header] = cell_content
                
                # Build narrative description
                narrative_parts = []
                
                # Start with study identification
                if 'article id' in study_info:
                    narrative_parts.append(f"Study {study_info['article id']}")
                else:
                    narrative_parts.append(f"Study {row_idx}")
                
                # Add study design information
                if 'study design' in study_info:
                    design = study_info['study design']
                    narrative_parts.append(f"employed a {design.lower()}")
                
                # Add sample size if available
                if 'sample size' in study_info:
                    sample = study_info['sample size']
                    if sample.isdigit():
                        narrative_parts.append(f"with {sample} participants")
                
                # Add intervention information
                if 'intervention' in study_info:
                    intervention = study_info['intervention']
                    if len(intervention) > 80:
                        intervention = intervention[:77] + "..."
                    narrative_parts.append(f"investigating {intervention.lower()}")
                
                # Add primary outcome
                if 'primary outcome' in study_info:
                    outcome = study_info['primary outcome']
                    if len(outcome) > 100:
                        outcome = outcome[:97] + "..."
                    narrative_parts.append(f"The primary outcome measured was {outcome.lower()}")
                
                # Add effect size if available
                if 'effect size' in study_info:
                    effect = study_info['effect size']
                    try:
                        effect_val = float(effect)
                        narrative_parts.append(f"with an effect size of {effect}")
                    except ValueError:
                        if len(effect) < 50:
                            narrative_parts.append(f"reporting {effect}")
                
                # Add limitations if present
                if 'limitations' in study_info:
                    limitations = study_info['limitations']
                    if len(limitations) > 120:
                        limitations = limitations[:117] + "..."
                    narrative_parts.append(f"Key limitations included: {limitations.lower()}")
                
                # Combine into readable narrative
                if len(narrative_parts) > 1:
                    narrative_text = ". ".join(narrative_parts[:3])  # First sentence
                    if len(narrative_parts) > 3:
                        narrative_text += ". " + ". ".join(narrative_parts[3:])
                    narrative_text += "."
                    
                    table_elements.append(Paragraph(narrative_text, narrative_style))
                    table_elements.append(Spacer(1, 6))
        
        return table_elements
        
    except Exception as e:
        # Ultimate simple fallback
        try:
            from reportlab.platypus import Paragraph
            from reportlab.lib.styles import getSampleStyleSheet
            styles = getSampleStyleSheet()
            
            simple_text = f"Table data contains {len(table_data)-1} studies with the following characteristics: " + \
                         ", ".join(table_data[0]) if table_data else "No table data available."
            
            return [Paragraph(simple_text, styles['Normal'])]
        except:
            return None

def process_inline_markdown(text):
    """Process inline markdown formatting like **bold**, *italic*, etc."""
    if not text:
        return text
    
    # Handle bold text **text**
    text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
    
    # Handle italic text *text*
    text = re.sub(r'\*(.*?)\*', r'<i>\1</i>', text)
    
    # Handle inline code `text`
    text = re.sub(r'`(.*?)`', r'<font name="Courier">\1</font>', text)
    
    # Escape any remaining angle brackets
    text = text.replace('<', '&lt;').replace('>', '&gt;')
    
    # Restore our formatting tags
    text = text.replace('&lt;b&gt;', '<b>').replace('&lt;/b&gt;', '</b>')
    text = text.replace('&lt;i&gt;', '<i>').replace('&lt;/i&gt;', '</i>')
    text = text.replace('&lt;font name="Courier"&gt;', '<font name="Courier">').replace('&lt;/font&gt;', '</font>')
    
    return text

def create_pdf_from_html(markdown_content, title="Systematic Review Report"):
    """Alternative PDF generation method using HTML conversion with better table handling."""
    if not PDF_AVAILABLE:
        return None
    
    try:
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import inch
        from reportlab.lib import colors
        import re
        
        # Convert markdown to HTML with table support
        html_content = markdown2.markdown(markdown_content, extras=['tables', 'fenced-code-blocks', 'markdown-in-html'])
        
        # Create a buffer to store PDF
        buffer = io.BytesIO()
        
        # Create PDF document
        doc = SimpleDocTemplate(buffer, pagesize=A4, 
                              rightMargin=inch, leftMargin=inch,
                              topMargin=inch, bottomMargin=inch)
        
        # Get styles
        styles = getSampleStyleSheet()
        
        # Custom styles
        h1_style = ParagraphStyle(
            'CustomH1',
            parent=styles['Heading1'],
            fontSize=16,
            spaceAfter=12,
            spaceBefore=20,
            textColor=colors.HexColor('#2c3e50')
        )
        
        h2_style = ParagraphStyle(
            'CustomH2',
            parent=styles['Heading2'],
            fontSize=14,
            spaceAfter=10,
            spaceBefore=16,
            textColor=colors.HexColor('#34495e')
        )
        
        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontSize=11,
            spaceAfter=6,
            leading=16
        )
        
        # Build story from HTML
        story = []
        
        # Handle tables separately
        table_pattern = r'<table[^>]*>(.*?)</table>'
        tables = re.findall(table_pattern, html_content, re.DOTALL)
        
        # Split content by tables
        content_parts = re.split(table_pattern, html_content, flags=re.DOTALL)
        
        for i, part in enumerate(content_parts):
            if part in tables:
                # This is a table - convert to reportlab table
                table_obj = convert_html_table_to_reportlab(part)
                if table_obj:
                    story.append(Spacer(1, 12))
                    story.append(table_obj)
                    story.append(Spacer(1, 12))
            else:
                # Regular content - process normally
                # Clean up HTML tags and convert to reportlab format
                processed_content = clean_html_content(part)
                
                # Split into paragraphs
                paragraphs = processed_content.split('\n\n')
                
                for para in paragraphs:
                    para = para.strip()
                    if para:
                        # Determine style based on content
                        if para.startswith('<h1>'):
                            text = re.sub(r'<[^>]+>', '', para)
                            story.append(Paragraph(text, h1_style))
                        elif para.startswith('<h2>'):
                            text = re.sub(r'<[^>]+>', '', para)
                            story.append(Paragraph(text, h2_style))
                        else:
                            # Clean any remaining HTML tags
                            clean_text = re.sub(r'<[^>]+>', '', para)
                            if clean_text.strip():
                                story.append(Paragraph(clean_text, normal_style))
                                story.append(Spacer(1, 6))
        
        # Build PDF
        doc.build(story)
        
        # Get PDF data
        pdf_data = buffer.getvalue()
        buffer.close()
        
        return pdf_data
        
    except Exception as e:
        st.error(f"Error creating PDF from HTML: {str(e)}")
        return None

def convert_html_table_to_reportlab(table_html):
    """Convert HTML table to reportlab Table object."""
    try:
        import re
        
        # Extract table rows
        row_pattern = r'<tr[^>]*>(.*?)</tr>'
        rows = re.findall(row_pattern, table_html, re.DOTALL)
        
        table_data = []
        
        for row in rows:
            # Extract cells (th or td)
            cell_pattern = r'<t[hd][^>]*>(.*?)</t[hd]>'
            cells = re.findall(cell_pattern, row, re.DOTALL)
            
            # Clean cell content
            clean_cells = []
            for cell in cells:
                # Remove HTML tags and clean up
                clean_cell = re.sub(r'<[^>]+>', '', cell).strip()
                clean_cells.append(clean_cell)
            
            if clean_cells:
                table_data.append(clean_cells)
        
        if table_data:
            return create_table_from_data(table_data)
        
        return None
        
    except Exception as e:
        st.error(f"Error converting HTML table: {str(e)}")
        return None

def clean_html_content(html_content):
    """Clean HTML content for better PDF conversion."""
    import re
    
    # Convert common HTML tags to reportlab-friendly format
    content = html_content
    
    # Headers
    content = re.sub(r'<h1[^>]*>(.*?)</h1>', r'<h1>\1</h1>', content)
    content = re.sub(r'<h2[^>]*>(.*?)</h2>', r'<h2>\1</h2>', content)
    content = re.sub(r'<h3[^>]*>(.*?)</h3>', r'<h3>\1</h3>', content)
    
    # Paragraphs
    content = re.sub(r'<p[^>]*>', '<p>', content)
    
    # Bold and italic
    content = content.replace('<strong>', '<b>').replace('</strong>', '</b>')
    content = content.replace('<em>', '<i>').replace('</em>', '</i>')
    
    # Lists
    content = re.sub(r'<ul[^>]*>', '', content)
    content = content.replace('</ul>', '')
    content = re.sub(r'<li[^>]*>', '• ', content)
    content = content.replace('</li>', '\n')
    
    # Remove remaining unwanted tags
    content = re.sub(r'</?div[^>]*>', '', content)
    content = re.sub(r'</?span[^>]*>', '', content)
    
    return content

def create_simple_html_for_pdf(markdown_content, title="Systematic Review Report"):
    """Create HTML content that can be used for PDF conversion."""
    try:
        # Convert markdown to HTML
        html_content = markdown2.markdown(markdown_content, extras=['tables', 'fenced-code-blocks'])
        
        # Create full HTML document
        full_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>{title}</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    margin: 40px;
                    color: #333;
                }}
                h1 {{
                    color: #2c3e50;
                    border-bottom: 2px solid #3498db;
                    padding-bottom: 10px;
                }}
                h2 {{
                    color: #34495e;
                    margin-top: 30px;
                }}
                h3 {{
                    color: #5d6d7e;
                }}
                table {{
                    border-collapse: collapse;
                    width: 100%;
                    margin: 20px 0;
                }}
                th, td {{
                    border: 1px solid #ddd;
                    padding: 8px;
                    text-align: left;
                }}
                th {{
                    background-color: #f2f2f2;
                }}
                code {{
                    background-color: #f4f4f4;
                    padding: 2px 4px;
                    border-radius: 3px;
                }}
                pre {{
                    background-color: #f4f4f4;
                    padding: 10px;
                    border-radius: 5px;
                    overflow-x: auto;
                }}
                .page-break {{
                    page-break-before: always;
                }}
            </style>
        </head>
        <body>
            {html_content}
        </body>
        </html>
        """
        
        return full_html
        
    except Exception as e:
        st.error(f"Error creating HTML: {str(e)}")
        return None

def show(logger):
    """Report generation page."""
    st.title(" Report Generation")
    st.markdown("---")

    # Check if project is selected
    project_id = st.session_state.get("current_project_id")
    if not project_id:
        st.warning(" Please select a project from the Dashboard first.")
        return

    logger.info(f"Loading report generation for project: {project_id}")

    # Load extracted data
    extracted_data = load_extracted_data(project_id)
    
    if extracted_data.empty:
        st.warning(" No extracted data available for report generation.")
        st.info(" **Next steps:** Complete the Full-Text Analysis phase to extract data from your articles.")
        return

    st.success(f"Found extracted data from {len(extracted_data)} articles")

    # Initialize Ollama client
    config = load_config()
    ollama_client = OllamaClient()

    # Create tabs for different report aspects
    tab1, tab2, tab3, tab4 = st.tabs([" Data Summary", " Report Generation", " Manual Editing", " Export"])

    with tab1:
        st.subheader("Extracted Data Summary")
        
        # Show data overview
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Articles Analyzed", len(extracted_data))
        
        with col2:
            if 'extraction_date' in extracted_data.columns:
                latest_extraction = extracted_data['extraction_date'].max()
                st.metric("Latest Extraction", latest_extraction.split(' ')[0] if latest_extraction else "Unknown")
        
        with col3:
            total_fields = len([col for col in extracted_data.columns if col not in ['article_id', 'title', 'extraction_date']])
            st.metric("Data Fields", total_fields)
        
        # Data completeness analysis
        st.markdown("**Data Completeness Analysis:**")
        
        completeness_data = []
        for col in extracted_data.columns:
            if col not in ['article_id', 'title', 'extraction_date']:
                non_empty = extracted_data[col].notna().sum()
                completeness = (non_empty / len(extracted_data)) * 100
                completeness_data.append({
                    'Field': col.replace('_', ' ').title(),
                    'Articles with Data': non_empty,
                    'Total Articles': len(extracted_data),
                    'Completeness %': f"{completeness:.1f}%"
                })
        
        completeness_df = pd.DataFrame(completeness_data)
        safe_dataframe(completeness_df, use_container_width=True)
        
        # Show extracted data table
        st.markdown("**Extracted Data Preview:**")
        
        # Prepare display data
        display_columns = ['title'] + [col for col in extracted_data.columns if col not in ['article_id', 'title', 'extraction_date']]
        display_data = extracted_data[display_columns].head(10)
        
        safe_dataframe(display_data, use_container_width=True)
        
        if len(extracted_data) > 10:
            st.info(f"Showing first 10 rows of {len(extracted_data)} total articles")

    with tab2:
        st.subheader("AI-Generated Report")
        
        # Check if extraction model is configured
        extraction_model = config.get("extraction_model", "")
        if not extraction_model:
            st.error(" No extraction model configured. Please configure models in Settings.")
            return
        
        st.info(f"Using model: **{extraction_model}**")
        
        # Report generation options
        st.markdown("**Report Configuration:**")
        
        col1, col2 = st.columns(2)
        
        with col1:
            report_type = st.selectbox(
                "Report Type",
                options=["Systematic Review", "Meta-Analysis", "Narrative Review", "Scoping Review"],
                index=0
            )
        
        with col2:
            include_tables = st.checkbox("Include Data Tables", value=True)
        
        report_sections = st.multiselect(
            "Report Sections to Include",
            options=["Abstract", "Introduction", "Methods", "Results", "Discussion", "Conclusion", "Limitations", "References"],
            default=["Abstract", "Methods", "Results", "Discussion", "Conclusion"]
        )
        
        # Additional instructions
        additional_instructions = st.text_area(
            "Additional Instructions for AI",
            placeholder="e.g., Focus on clinical implications, include statistical analysis, emphasize methodological quality...",
            height=100
        )
        
        # Generate report button
        if st.button(" Generate AI Report", use_container_width=True):
            with st.spinner("Generating comprehensive report... This may take a few minutes."):
                try:
                    # Prepare data for report generation
                    data_summary = extracted_data.to_string(index=False)
                    
                    # Create enhanced prompt
                    prompt_context = f"""
                    Report Type: {report_type}
                    Sections to Include: {', '.join(report_sections)}
                    Include Tables: {include_tables}
                    Additional Instructions: {additional_instructions}
                    
                    Number of Studies: {len(extracted_data)}
                    Data Fields: {', '.join([col for col in extracted_data.columns if col not in ['article_id', 'title', 'extraction_date']])}
                    """
                    
                    generated_report = ollama_client.generate_report(f"{prompt_context}\n\nExtracted Data:\n{data_summary}")
                    
                    if generated_report and "Failed to generate report" not in generated_report:
                        st.session_state.generated_report = generated_report
                        logger.success("AI report generated successfully")
                        st.success(" Report generated successfully!")
                        st.rerun()
                    else:
                        logger.error("Failed to generate AI report")
                        st.error(" Failed to generate report. Please try again.")
                        
                except Exception as e:
                    logger.error(f"Error generating report: {str(e)}")
                    st.error(f" Error generating report: {str(e)}")
        
        # Display generated report
        if 'generated_report' in st.session_state:
            st.markdown("**Generated Report:**")
            
            report_content = st.session_state.generated_report
            
            # Show report in a text area for preview
            st.markdown(report_content)
            
            # Save generated report
            col1, col2 = st.columns([1, 1])
            
            with col1:
                if st.button(" Save Generated Report"):
                    save_final_report(project_id, report_content)
                    logger.success("Generated report saved")
                    st.success("Report saved successfully!")
            
            with col2:
                if st.button(" Edit Report"):
                    st.session_state.manual_report = report_content
                    logger.info("Report moved to manual editing")
                    st.info("Report moved to Manual Editing tab for further customization")

    with tab3:
        st.subheader("Manual Report Editing")
        
        # Load existing report or start with generated report
        existing_report = load_final_report(project_id)
        
        if 'manual_report' not in st.session_state:
            if existing_report:
                st.session_state.manual_report = existing_report
            else:
                st.session_state.manual_report = ""
        
        # Manual editing interface
        st.markdown("**Edit your report manually:**")
        
        manual_report = st.text_area(
            "Report Content (Markdown supported)",
            value=st.session_state.manual_report,
            height=600,
            help="You can use Markdown formatting for headers, lists, tables, etc."
        )
        
        # Update session state
        st.session_state.manual_report = manual_report
        
        # Report metadata
        col1, col2 = st.columns(2)
        
        with col1:
            report_title = st.text_input(
                "Report Title",
                value=f"Systematic Review: {st.session_state.get('current_project_title', 'Untitled Project')}"
            )
        
        with col2:
            authors = st.text_input(
                "Authors",
                placeholder="e.g., Smith, J., Doe, A."
            )
        
        # Additional metadata
        keywords = st.text_input(
            "Keywords",
            placeholder="e.g., systematic review, meta-analysis, healthcare"
        )
        
        # Save manual report
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button(" Save Draft", use_container_width=True):
                # Add metadata to report
                full_report = f"""# {report_title}

**Authors:** {authors}
**Keywords:** {keywords}
**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

{manual_report}
"""
                
                save_final_report(project_id, full_report)
                st.session_state.manual_report = full_report
                logger.success("Report draft saved")
                st.success("Draft saved successfully!")
        
        with col2:
            if st.button("👁️ Preview", use_container_width=True):
                st.markdown("**Preview:**")
                st.markdown(manual_report)
        
        with col3:
            if st.button(" Reset", use_container_width=True):
                st.session_state.manual_report = existing_report or ""
                st.rerun()

    with tab4:
        st.subheader("Export & Download")
        
        # Load final report
        final_report = load_final_report(project_id)
        
        if not final_report:
            st.warning(" No report available for export. Please generate or create a report first.")
        else:
            st.success(" Report ready for export")
            
            # Export options
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**Download Options:**")
                
                # Download as Markdown
                safe_download_button(
                    label="📄 Download as Markdown (.md)",
                    data=final_report,
                    file_name=f"systematic_review_{project_id}_{datetime.now().strftime('%Y%m%d')}.md",
                    mime="text/markdown",
                    use_container_width=True
                )
                
                # Download as PDF
                if PDF_AVAILABLE:
                    st.success("✅ PDF export is available!")
                    
                    # PDF generation options
                    pdf_method = st.radio(
                        "PDF Generation Method:",
                        options=["Standard", "HTML-based"],
                        help="Standard: Direct markdown parsing. HTML-based: Convert to HTML first (better for complex formatting)"
                    )
                    
                    col_pdf1, col_pdf2 = st.columns(2)
                    
                    with col_pdf1:
                        if st.button("📋 Generate PDF", use_container_width=True):
                            with st.spinner("Generating PDF... Please wait."):
                                if pdf_method == "HTML-based":
                                    pdf_data = create_pdf_from_html(final_report, f"Systematic Review - {project_id}")
                                else:
                                    pdf_data = create_pdf_from_markdown(final_report, f"Systematic Review - {project_id}")
                                
                                if pdf_data:
                                    st.session_state.pdf_data = pdf_data
                                    st.session_state.pdf_filename = f"systematic_review_{project_id}_{datetime.now().strftime('%Y%m%d')}.pdf"
                                    st.session_state.pdf_method = pdf_method
                                    st.success(f"✅ PDF generated successfully using {pdf_method} method!")
                                    st.rerun()
                                else:
                                    st.error("❌ Failed to generate PDF")
                    
                    with col_pdf2:
                        if 'pdf_data' in st.session_state:
                            method_used = st.session_state.get('pdf_method', 'Standard')
                            st.info(f"Generated using: {method_used} method")
                            safe_download_button(
                                label="📥 Download PDF",
                                data=st.session_state.pdf_data,
                                file_name=st.session_state.pdf_filename,
                                mime="application/pdf",
                                use_container_width=True,
                                key="pdf_download"
                            )
                    
                    # Alternative HTML download for PDF conversion
                    st.markdown("---")
                    st.markdown("**Alternative Options:**")
                    if st.button("🌐 Download HTML (for PDF conversion)", use_container_width=True):
                        html_content = create_simple_html_for_pdf(final_report, f"Systematic Review - {project_id}")
                        if html_content:
                            safe_download_button(
                                label="📥 Download HTML",
                                data=html_content,
                                file_name=f"systematic_review_{project_id}_{datetime.now().strftime('%Y%m%d')}.html",
                                mime="text/html",
                                use_container_width=True,
                                key="html_download",
                                help="Download as HTML - you can open this in a browser and print to PDF"
                            )
                else:
                    st.warning("📋 PDF export requires additional packages.")
                    st.info("The required packages (reportlab, markdown2) are not installed.")
                    
                    with st.expander("📦 Installation Instructions", expanded=False):
                        st.markdown("""
                        **To enable PDF export, install the required packages:**
                        
                        1. **If using the virtual environment (recommended):**
                        ```bash
                        cd /path/to/OpenDeepResearcher
                        source venv/bin/activate  # On Windows: venv\\Scripts\\activate
                        pip install reportlab markdown2
                        ```
                        
                        2. **If using system Python:**
                        ```bash
                        pip install reportlab markdown2
                        ```
                        
                        3. **After installation, restart the Streamlit application.**
                        """)
                    
                    # Fallback HTML option
                    st.markdown("**Alternative: Download as HTML**")
                    if st.button("🌐 Download as HTML", use_container_width=True):
                        html_content = create_simple_html_for_pdf(final_report, f"Systematic Review - {project_id}")
                        if html_content:
                            safe_download_button(
                                label="📥 Download HTML",
                                data=html_content,
                                file_name=f"systematic_review_{project_id}_{datetime.now().strftime('%Y%m%d')}.html",
                                mime="text/html",
                                use_container_width=True,
                                key="html_fallback_download",
                                help="Open in browser and use 'Print to PDF' for PDF conversion"
                            )
                
                # Download extracted data as CSV
                if not extracted_data.empty:
                    csv_data = extracted_data.to_csv(index=False)
                    safe_download_button(
                        label="📊 Download Extracted Data (.csv)",
                        data=csv_data,
                        file_name=f"extracted_data_{project_id}_{datetime.now().strftime('%Y%m%d')}.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
            
            with col2:
                st.markdown("**Report Statistics:**")
                
                word_count = len(final_report.split())
                char_count = len(final_report)
                line_count = len(final_report.split('\n'))
                
                st.metric("Word Count", word_count)
                st.metric("Character Count", char_count)
                st.metric("Line Count", line_count)
            
            # Report preview
            st.markdown("---")
            st.markdown("**Final Report Preview:**")
            
            with st.expander("📖 View Full Report", expanded=False):
                st.markdown(final_report)
            
            # Quality checklist
            st.markdown("---")
            st.markdown("**Quality Checklist:**")
            
            checklist_items = [
                "Research question clearly stated",
                "Search strategy described",
                "Inclusion/exclusion criteria defined",
                "Study selection process documented",
                "Data extraction methods explained",
                "Results appropriately synthesized",
                "Limitations acknowledged",
                "Conclusions supported by evidence"
            ]
            
            for item in checklist_items:
                st.checkbox(item, key=f"checklist_{item}")
            
            # Final actions
            st.markdown("---")
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("📧 Prepare for Submission", use_container_width=True):
                    st.info("""
                    **Submission Preparation Checklist:**
                    - [ ] Format according to journal guidelines
                    - [ ] Include required sections
                    - [ ] Check citation format
                    - [ ] Review word count limits
                    - [ ] Prepare supplementary materials
                    """)
            
            with col2:
                if st.button("🎯 Project Complete", use_container_width=True):
                    # Mark project as complete
                    from utils.data_manager import load_projects, save_projects
                    projects_df = load_projects()
                    projects_df.loc[projects_df['project_id'] == project_id, 'status'] = 'Complete'
                    save_projects(projects_df)
                    
                    logger.success("Project marked as complete")
                    st.success("🎉 Project marked as complete! Congratulations on finishing your systematic review!")

# Legacy function for backward compatibility
def display_report():
    """Legacy function - use show() instead."""
    if 'logger' not in st.session_state:
        from components.logger import Logger
        st.session_state.logger = Logger()
    show(st.session_state.logger)