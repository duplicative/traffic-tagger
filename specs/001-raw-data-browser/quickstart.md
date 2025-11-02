# Quickstart: Raw Data Browser

**Date**: 2025-11-02

This document provides a brief guide on how to use the new Raw Data Browser feature.

## Accessing the Raw Data Browser

1.  Start the `traffic-tagger` application as usual.
2.  In the web interface, you will see a new tab or navigation item labeled "Raw Data Browser".
3.  Click on this tab to access the new view.

## Using the Filters

The Raw Data Browser allows you to filter the records based on their source and category.

-   **Source Filter**: Use the source filter to switch between records from `csv` files and the `sidecar` extension.
-   **Category Filter**: When the `sidecar` source is selected, you can use the category filter to further narrow down the results to `dom_snapshots`, `js_executions`, or `storage_states`.

## Viewing Raw Data

-   The records are displayed in a list, with pagination for large datasets.
-   Each record is displayed as a JSON object. The JSON is syntax-highlighted for readability.
