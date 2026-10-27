# CloudCart — Cloud-Based E-Commerce Application

CloudCart is a cloud-deployed e-commerce web application that allows users to browse products, manage their shopping carts, securely register and log in, place orders, and view their order history. The project demonstrates the integration of web development, relational database management, and cloud computing services to build an accessible online shopping platform.

## Features

- **User Authentication:** User registration, login, and logout functionality.
- **Product Catalog:** Browse available products with prices and details.
- **Shopping Cart:** Add products to the cart and remove unwanted items.
- **Checkout System:** Place orders and save order information to the database.
- **Order Management:** View order history and individual order details.
- **Cloud Database:** Store user, product, and order data using a managed MySQL database.
- **Cloud Deployment:** Deploy the web application using Vercel and host the database on Aiven.
- **Responsive Interface:** A clean shopping interface designed for a convenient user experience.

## Technology Stack

- **Frontend:** HTML5, CSS3
- **Backend:** Python, Flask
- **Authentication:** Flask-Login
- **Database:** MySQL 8.4
- **Cloud Database Hosting:** Aiven
- **Application Deployment:** Vercel
- **Version Control:** Git and GitHub
- **Development Environment:** Visual Studio Code

## System Architecture

CloudCart uses a web-based architecture in which users access the application through a browser. The Flask backend processes requests and manages application logic, while the MySQL database hosted on Aiven stores persistent application data. The application is deployed on Vercel, and GitHub is used for source-code management and the deployment workflow.

## Project Objective

The primary objective of CloudCart is to demonstrate how cloud computing services can be used to develop and deploy an e-commerce application with centralized data storage, user authentication, shopping cart functionality, and order management.

## Future Enhancements

- Admin dashboard for adding, editing, and managing products.
- Online payment gateway integration.
- Product search, filtering, and category management.
- Inventory tracking and stock management.
- Automated testing, monitoring, and performance evaluation.

## Live Demo

https://cloudcart-chi.vercel.app/

## Source Code

https://github.com/Ragul-Krishnann/Cloudcart

---

**Note:** This project is an educational prototype. The current checkout records orders but does not process real online payments.
