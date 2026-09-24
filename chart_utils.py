import plotly.express as px
import pandas as pd

def generate_chart(df, chart_type, title=None, x_label=None, y_label=None, order_list=None, x_col=None, y_col=None):
    """
    Generate a Plotly figure based on the dataframe and chart type.
    
    Args:
        df (pd.DataFrame): The data.
        chart_type (str): 'bar', 'line', or 'pie'.
        title (str): Chart title.
        x_label (str): Label for X axis (or names for pie).
        y_label (str): Label for Y axis (or values for pie).
        order_list (list): List of values for the categorical axis to sort/order by.
        x_col (str): Column name for X axis.
        y_col (str): Column name for Y axis.
    
    Returns:
        plotly.graph_objects.Figure
    """
    if df.empty:
        return None

    # heuristics for columns
    # Find first string column for categories/X
    # Find numeric columns for values/Y
    
    str_cols = df.select_dtypes(include=['object', 'string']).columns
    num_cols = df.select_dtypes(include=['number']).columns
    
    # Determine X Column (Category)
    if x_col and x_col in df.columns:
        cat_col = x_col
    elif len(str_cols) > 0:
        cat_col = str_cols[0]
    else:
        cat_col = df.index.name if df.index.name else "Index"
    
    # Determine Y Column (Value)
    if y_col and y_col in df.columns:
        val_col = y_col
    elif len(num_cols) > 0:
        val_col = num_cols[0] # Default to first numeric
    elif len(df.columns) > 1:
        val_col = df.columns[1] # Fallback to second column
    else:
        return None # Can't plot without at least two columns

    # Apply ordering if provided
    # For Bar/Line, this means sorting the DF or setting category order
    layout_args = {}
    if title:
        layout_args['title'] = title
        
    # Reorder DF if order_list is provided and matches cat_col
    if order_list and cat_col in df.columns:
        # Check if order_list items are in the column
        # Only reorder if there is a significant overlap to avoid destroying data
        # when the user switches X-axis to a numeric column but order_list is for a string column
        col_values = set(df[cat_col].astype(str))
        order_values_in_col = [x for x in order_list if str(x) in col_values]
        
        if len(order_values_in_col) > 0:
             try:
                 df = df.set_index(cat_col).reindex(order_list).reset_index()
             except:
                 pass # Fallback if reindexing fails

    try:
        if chart_type == 'bar':
            fig = px.bar(df, x=cat_col, y=val_col, title=title)
            fig.update_layout(
                title_x=0.5,
                xaxis_title=x_label if x_label else cat_col,
                yaxis=dict(
                    title=dict(
                        text=y_label if y_label else val_col,
                        standoff=20
                    )
                )
            )
        
        elif chart_type == 'line':
            fig = px.line(df, x=cat_col, y=val_col, title=title)
            fig.update_layout(
                title_x=0.5,
                xaxis_title=x_label if x_label else cat_col,
                yaxis=dict(
                    title=dict(
                        text=y_label if y_label else val_col,
                        standoff=20
                    )
                )
            )
            
        elif chart_type == 'pie':
            # For pie, names=cat_col, values=val_col
            fig = px.pie(df, names=cat_col, values=val_col, title=title)
            fig.update_layout(title_x=0.5)
            # "show lables on teh slices" -> textinfo
            fig.update_traces(textposition='inside', textinfo='percent+label')
        else:
            return None
            
        # Update labels if provided (labels arg in px is easier but update_layout is safer for post-creation)
        # Actually px handles labels in the `labels` dict arg, but update_layout works for axes.
        
        return fig
    except Exception as e:
        print(f"Error generating chart: {e}")
        return None
