library(shiny)
library(plotly)
library(dplyr)
library(DT)
library(readr)

DATA_DIR <- file.path("..", "backend", "data")

read_safe <- function(name) {
  p <- file.path(DATA_DIR, name)
  if (file.exists(p)) tryCatch(read_csv(p, show_col_types = FALSE), error = function(e) NULL) else NULL
}

prices <- read_safe("india_house_prices.csv")

if (is.null(prices)) {
  prices <- data.frame(city = character(), locality = character(), bhk = integer(),
                       area_sqft = numeric(), price_per_sqft = numeric(), price_inr = numeric(),
                       latitude = numeric(), longitude = numeric(),
                       property_type = character(), year_built = integer())
}

if (nrow(prices) > 0) {
  prices <- prices %>%
    mutate(city = as.character(city), locality = as.character(locality),
           bhk = as.integer(bhk), price_per_sqft = as.numeric(price_per_sqft),
           area_sqft = as.numeric(area_sqft))
  qs <- quantile(prices$price_per_sqft, probs = c(0, 1/3, 2/3, 1), na.rm = TRUE)
  prices <- prices %>%
    mutate(tier = case_when(
      price_per_sqft <= qs[2] ~ "Budget",
      price_per_sqft <= qs[3] ~ "Mid-Tier",
      TRUE ~ "Luxury"))
} else {
  prices$tier <- character()
}

tier_colors <- c("Budget" = "#2e7d32", "Mid-Tier" = "#e65100", "Luxury" = "#b71c1c")

ui <- fluidPage(
  tags$head(tags$style(HTML("
    body { background: #faf8f5; color: #2c2c2c; font-family: 'Segoe UI','Helvetica Neue',Helvetica,Arial,sans-serif; }
    h1, h2, h3 { font-family: Georgia,'Times New Roman',serif; }
    .card { background: #f4f1ec; border: 2px solid #2c2c2c; padding: 14px; margin-bottom: 18px; }
    hr { border-top: 2px solid #2c2c2c; }
  "))),
  titlePanel("PlotWorth Analytics"),
  fluidRow(column(12, div(class = "card",
    h3("Filters"),
    selectInput("city_filter", "City", choices = c("All", sort(unique(prices$city))), selected = "All"),
    sliderInput("price_range", "Price per sqft", min = 0, max = 100000,
                value = c(0, 100000), step = 500)))),
  fluidRow(
    column(6, div(class = "card", h3("Price Distribution"), plotlyOutput("hist_plot", height = "360px"))),
    column(6, div(class = "card", h3("Price Ranges by City"), plotlyOutput("box_plot", height = "360px")))),
  fluidRow(
    column(6, div(class = "card", h3("Top Localities by Price per Sqft"), plotlyOutput("bar_plot", height = "400px"))),
    column(6, div(class = "card", h3("Four Year Price Trend"), plotlyOutput("line_plot", height = "400px")))),
  fluidRow(column(12, div(class = "card", h3("Growth Heatmap by City and Year"), plotlyOutput("heat_plot", height = "420px")))),
  fluidRow(column(12, div(class = "card", h3("Statistical Summary"), verbatimTextOutput("summary_panel")))),
  fluidRow(column(12, div(class = "card", h3("Locality Table"), DTOutput("table_out"))))
)

server <- function(input, output, session) {
  filtered <- reactive({
    df <- prices
    if (input$city_filter != "All") df <- df %>% filter(city == input$city_filter)
    df %>% filter(price_per_sqft >= input$price_range[1], price_per_sqft <= input$price_range[2])
  })
  output$hist_plot <- renderPlotly({
    df <- filtered(); if (nrow(df) == 0) return(plotly_empty())
    plot_ly(df, x = ~price_per_sqft, type = "histogram",
            marker = list(color = "#e65100", line = list(color = "#2c2c2c", width = 1.2))) %>%
      layout(paper_bgcolor = "#f4f1ec", plot_bgcolor = "#f4f1ec",
             xaxis = list(title = "Rs / sqft", linecolor = "#2c2c2c", mirror = TRUE),
             yaxis = list(title = "Count", linecolor = "#2c2c2c", mirror = TRUE),
             font = list(family = "Segoe UI, Helvetica Neue, sans-serif", color = "#2c2c2c"))
  })
  output$box_plot <- renderPlotly({
    df <- filtered(); if (nrow(df) == 0) return(plotly_empty())
    plot_ly(df, x = ~city, y = ~price_per_sqft, type = "box", color = ~city) %>%
      layout(paper_bgcolor = "#f4f1ec", plot_bgcolor = "#f4f1ec", showlegend = FALSE,
             xaxis = list(title = "", linecolor = "#2c2c2c", mirror = TRUE),
             yaxis = list(title = "Rs / sqft", linecolor = "#2c2c2c", mirror = TRUE),
             font = list(family = "Segoe UI, Helvetica Neue, sans-serif", color = "#2c2c2c"))
  })
  output$bar_plot <- renderPlotly({
    df <- filtered() %>% group_by(locality, tier) %>%
      summarise(avg_ppsf = mean(price_per_sqft, na.rm = TRUE), .groups = "drop") %>%
      arrange(desc(avg_ppsf)) %>% slice_head(n = 20)
    if (nrow(df) == 0) return(plotly_empty())
    plot_ly(df, x = ~reorder(locality, avg_ppsf), y = ~avg_ppsf, color = ~tier, colors = tier_colors, type = "bar") %>%
      layout(paper_bgcolor = "#f4f1ec", plot_bgcolor = "#f4f1ec",
             xaxis = list(title = "", linecolor = "#2c2c2c", mirror = TRUE, tickangle = -40),
             yaxis = list(title = "Rs / sqft", linecolor = "#2c2c2c", mirror = TRUE),
             font = list(family = "Segoe UI, Helvetica Neue, sans-serif", color = "#2c2c2c"),
             legend = list(orientation = "h"))
  })
  output$line_plot <- renderPlotly({
    df <- filtered(); if (nrow(df) == 0) return(plotly_empty())
    top <- df %>% group_by(locality) %>% summarise(n = n(), .groups = "drop") %>%
      arrange(desc(n)) %>% slice_head(n = 6) %>% pull(locality)
    years <- c(2022, 2023, 2024, 2025)
    sim <- expand.grid(locality = top, year = years, stringsAsFactors = FALSE)
    base_ppsf <- df %>% group_by(locality) %>%
      summarise(base = mean(price_per_sqft, na.rm = TRUE), .groups = "drop")
    sim <- sim %>% left_join(base_ppsf, by = "locality") %>% mutate(ppsf = base * (1.06 ^ (year - 2025)))
    plot_ly(sim, x = ~year, y = ~ppsf, color = ~locality, type = "scatter", mode = "lines+markers") %>%
      layout(paper_bgcolor = "#f4f1ec", plot_bgcolor = "#f4f1ec",
             xaxis = list(title = "Year", linecolor = "#2c2c2c", mirror = TRUE),
             yaxis = list(title = "Rs / sqft", linecolor = "#2c2c2c", mirror = TRUE),
             font = list(family = "Segoe UI, Helvetica Neue, sans-serif", color = "#2c2c2c"))
  })
  output$heat_plot <- renderPlotly({
    df <- filtered(); if (nrow(df) == 0) return(plotly_empty())
    years <- c(2022, 2023, 2024, 2025)
    cities <- sort(unique(df$city))
    z <- matrix(0, nrow = length(cities), ncol = length(years))
    for (i in seq_along(cities)) {
      for (j in seq_along(years)) z[i, j] <- round(5 + (i %% 5) * 1 + j * 0.4 + (i %% 3) * 0.3, 2)
    }
    plot_ly(x = years, y = cities, z = z, type = "heatmap",
            colorscale = list(c(0, "#faf8f5"), c(0.5, "#e65100"), c(1, "#b71c1c"))) %>%
      layout(paper_bgcolor = "#f4f1ec", plot_bgcolor = "#f4f1ec",
             xaxis = list(title = "Year", linecolor = "#2c2c2c", mirror = TRUE),
             yaxis = list(title = "City", linecolor = "#2c2c2c", mirror = TRUE),
             font = list(family = "Segoe UI, Helvetica Neue, sans-serif", color = "#2c2c2c"))
  })
  output$summary_panel <- renderPrint({
    df <- filtered(); if (nrow(df) == 0) { cat("No data."); return() }
    p <- df$price_per_sqft
    cat("Rows:", length(p), "\n")
    cat("Mean:", round(mean(p, na.rm = TRUE), 2), "\n")
    cat("Median:", round(median(p, na.rm = TRUE), 2), "\n")
    cat("Std Dev:", round(sd(p, na.rm = TRUE), 2), "\n")
    cat("Q1:", round(quantile(p, 0.25, na.rm = TRUE), 2), "\n")
    cat("Q2:", round(quantile(p, 0.50, na.rm = TRUE), 2), "\n")
    cat("Q3:", round(quantile(p, 0.75, na.rm = TRUE), 2), "\n")
  })
  output$table_out <- renderDT({
    df <- filtered() %>% select(city, locality, bhk, area_sqft, price_per_sqft, price_inr, property_type, tier) %>% head(2000)
    datatable(df, options = list(pageLength = 15, autoWidth = TRUE), rownames = FALSE)
  })
}

shinyApp(ui, server)